#!/usr/bin/env python3
"""
Instagram Comment Scraper - Consolidated Version
Scrapes comments from Instagram posts and saves to CSV format
"""

import os
import sys
import json
import requests
import re
import csv
import click
from loguru import logger
from time import sleep
from typing import List, Dict, Any

# GraphQL Configuration
PARENT_QUERY_HASH = "97b41c52301f77ce508f55e66d17620e"
REPLY_QUERY_HASH = "863813fb3a4d6501723f11d1e44a42b1"
COMMENTS_PER_PAGE = 50

def read_post_ids_from_csv(filename: str) -> List[str]:
    """Read post IDs from CSV file"""
    ids = []
    try:
        with open(filename, 'r', newline='', encoding='utf-8') as csv_file:
            reader = csv.reader(csv_file)
            next(reader, None)  # Skip header
            for row in reader:
                if row and row[0].strip():
                    ids.append(row[0].strip())
    except FileNotFoundError:
        logger.error(f"Error: File '{filename}' not found.")
        return []
    return ids

def build_headers(shortcode: str, cookies_str: str) -> Dict[str, str]:
    """Build HTTP headers for API requests"""
    return {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-A125F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "X-Requested-With": "XMLHttpRequest",
        "X-IG-App-ID": "936619743392459",
        "Referer": f"https://www.instagram.com/p/{shortcode}/",
        "Cookie": cookies_str
    }

def graphql_request(query_hash: str, variables: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
    """Make GraphQL request to Instagram API"""
    var_str = json.dumps(variables, separators=(",", ":"))
    url = (
        f"https://www.instagram.com/graphql/query/"
        f"?query_hash={query_hash}"
        f"&variables={requests.utils.quote(var_str)}"
    )
    
    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"[!] HTTP error for {query_hash}: {e}")
        return {}

def fetch_replies(shortcode: str, comment_id: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
    """Fetch replies for a main comment"""
    all_replies = []
    has_next = True
    cursor = ""
    
    while has_next:
        vars = {
            "comment_id": comment_id, 
            "first": COMMENTS_PER_PAGE
        }
        if cursor:
            vars["after"] = cursor
        
        data = graphql_request(REPLY_QUERY_HASH, vars, headers)
        
        try:
            edge_info = data.get("data", {}).get("comment", {}).get("edge_threaded_comments", {})
            if not edge_info:
                logger.warning(f"No replies found for comment ID: {comment_id}")
                break
                
            edges = edge_info.get("edges", [])
            for edge in edges:
                node = edge.get("node", {})
                if node:
                    all_replies.append({
                        "post_id": shortcode,
                        "parent_comment_id": comment_id,
                        "comment_id": node.get("id"),
                        "username": node.get("owner", {}).get("username"),
                        "comment_text": node.get("text"),
                        "created_at": node.get("created_at"),
                        "is_reply": True
                    })
            
            page_info = edge_info.get("page_info", {})
            has_next = page_info.get("has_next_page", False)
            cursor = page_info.get("end_cursor", "")
        except KeyError as e:
            logger.error(f"[!] Error parsing reply data: {e}")
            break
            
        if has_next:
            sleep(2)  # Rate limiting
            
    return all_replies

def fetch_comments(shortcode: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
    """Fetch main comments and replies from a post"""
    all_comments = []
    has_next = True
    cursor = ""
    
    logger.info(f"Starting to fetch comments for post {shortcode}...")
    
    while has_next:
        vars = {"shortcode": shortcode, "first": COMMENTS_PER_PAGE}
        if cursor:
            vars["after"] = cursor
            
        data = graphql_request(PARENT_QUERY_HASH, vars, headers)

        if not data or not data.get("data", {}).get("shortcode_media", {}):
            logger.error(f"Invalid data or failed request for post {shortcode}. Skipping.")
            break

        try:
            edge_info = data.get("data", {}).get("shortcode_media", {}).get("edge_media_to_parent_comment", {})
            if not edge_info:
                logger.warning(f"No main comments found for post {shortcode}")
                break
            
            edges = edge_info.get("edges", [])
            for edge in edges:
                node = edge.get("node", {})
                if node:
                    parent_comment_id = node.get("id")
                    
                    # Add main comment
                    all_comments.append({
                        "post_id": shortcode,
                        "parent_comment_id": parent_comment_id,
                        "comment_id": parent_comment_id,
                        "username": node.get("owner", {}).get("username"),
                        "comment_text": node.get("text"),
                        "created_at": node.get("created_at"),
                        "is_reply": False
                    })
                    
                    # Check and fetch replies if any
                    child_comment_count = node.get("edge_threaded_comments", {}).get("count", 0)
                    if child_comment_count > 0:
                        logger.info(f"Fetching {child_comment_count} replies for comment ID: {parent_comment_id}")
                        replies = fetch_replies(shortcode, parent_comment_id, headers)
                        all_comments.extend(replies)
            
            page_info = edge_info.get("page_info", {})
            has_next = page_info.get("has_next_page", False)
            cursor = page_info.get("end_cursor", "")
            
        except (KeyError, TypeError) as e:
            logger.error(f"[!] Error parsing data for {shortcode}: {e}")
            break

        if has_next:
            logger.info("Fetching next page of comments...")
            sleep(2)  # Rate limiting
            
    return all_comments

@click.command(help='Instagram Comment Scraper')
@click.version_option(version='2.0.0', prog_name='Instagram Comment Scraper')
@click.option(
    "--input-file",
    default='instagram_urls.csv',
    help='Input CSV file with Instagram post IDs'
)
@click.option(
    "--output",
    default='data/instagram/all_comments.csv',
    help='Output file for all comments'
)
@click.option(
    "--sessionid",
    required=True,
    help='Instagram session ID cookie'
)
@click.option(
    "--ds-user-id",
    required=True,
    help='Instagram ds_user_id cookie'
)
@click.option(
    "--csrftoken",
    required=True,
    help='Instagram CSRF token cookie'
)
@click.option(
    "--mid",
    required=True,
    help='Instagram mid cookie'
)
def main(input_file: str, output: str, sessionid: str, ds_user_id: str, csrftoken: str, mid: str):
    """Main function to run Instagram comment scraper"""
    cookies_str = f"sessionid={sessionid}; ds_user_id={ds_user_id}; csrftoken={csrftoken}; mid={mid};"
    
    # Read IDs from file
    ids_to_scrape = read_post_ids_from_csv(input_file)
    
    if not ids_to_scrape:
        logger.error(f"No post IDs found in {input_file}.")
        sys.exit(1)
        
    all_comments_data = []

    for post_id in ids_to_scrape:
        logger.info(f"Processing post ID: {post_id}")
        headers = build_headers(post_id, cookies_str)
        comments = fetch_comments(post_id, headers)
        all_comments_data.extend(comments)

    # Save data to CSV file
    if all_comments_data:
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Get all fieldnames from all dictionaries
        all_keys = set()
        for d in all_comments_data:
            all_keys.update(d.keys())
        fieldnames = sorted(list(all_keys))

        with open(output, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_comments_data)
        
        logger.success(f"Successfully saved {len(all_comments_data)} comments to {output}")
    else:
        logger.warning("No comments were successfully retrieved to save.")

if __name__ == "__main__":
    main()
