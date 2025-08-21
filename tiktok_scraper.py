#!/usr/bin/env python3
"""
TikTok Comment Scraper - Consolidated Version
Scrapes comments from TikTok videos and saves to CSV format
"""

import jmespath
import json
import csv
import os
import click
from typing import Any, Dict, Iterator, List, Optional
from requests import Session, Response
from loguru import logger
from datetime import datetime
from dataclasses import dataclass, asdict

@dataclass
class Comment:
    """Data class for individual comment"""
    comment_id: str
    username: str
    nickname: str
    comment: str
    create_time: int
    avatar: str
    total_reply: int
    replies: List['Comment'] = None
    
    def __post_init__(self):
        if self.replies is None:
            self.replies = []

@dataclass
class Comments:
    """Data class for collection of comments"""
    caption: str
    video_url: str
    comments: List[Comment]
    has_more: bool
    
    @property
    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for compatibility"""
        return {
            'caption': self.caption,
            'video_url': self.video_url,
            'comments': [asdict(comment) for comment in self.comments],
            'has_more': self.has_more
        }

class TiktokComment:
    """TikTok comment scraper class"""
    BASE_URL: str = 'https://www.tiktok.com'
    API_URL: str = f'{BASE_URL}/api'

    def __init__(self) -> None:
        self.__session: Session = Session()
        self.aweme_id: str = ""
    
    def __parse_comment(self, data: Dict[str, Any]) -> Comment:
        """Parse comment data from API response"""
        parsed_data: Dict[str, Any] = jmespath.search(
            """
            {
                comment_id: cid,
                username: user.unique_id,
                nickname: user.nickname,
                comment: text,
                create_time: create_time,
                avatar: user.avatar_thumb.url_list[0],
                total_reply: reply_comment_total
            }
            """,
            data
        )
    
        comment: Comment = Comment(
            **parsed_data,
            replies=list(
                self.get_all_replies(parsed_data.get('comment_id'))
            ) if parsed_data.get('total_reply') else []
        )

        logger.info(f'{comment.create_time} - {comment.username}: {comment.comment}')
        return comment

    def get_all_replies(self, comment_id: str) -> Iterator[Comment]:
        """Get all replies for a comment"""
        page: int = 1
        while True:
            replies = self.get_replies(comment_id=comment_id, page=page)
            if not replies:
                break
            for reply in replies:
                yield reply
            page += 1

    def get_replies(self, comment_id: str, size: Optional[int] = 50, page: Optional[int] = 1):
        """Get replies for a specific comment"""
        response: Response = self.__session.get(
            f'{self.API_URL}/comment/list/reply/',
            params={
                'aid': 1988,
                'comment_id': comment_id,
                'item_id': self.aweme_id,
                'count': size,
                'cursor': (page - 1) * size
            }
        )

        return [
            self.__parse_comment(comment) 
            for comment in response.json().get('comments', [])
        ]
    
    def get_all_comments(self, aweme_id: str) -> Comments:
        """Get all comments for a video"""
        page: int = 1
        data: Comments = self.get_comments(aweme_id=aweme_id, page=page)
        
        while True:
            page += 1
            comments: Comments = self.get_comments(aweme_id=aweme_id, page=page)
            if not comments.has_more:
                break
            data.comments.extend(comments.comments)

        return data

    def get_comments(self, aweme_id: str, size: Optional[int] = 50, page: Optional[int] = 1) -> Comments:
        """Get comments for a specific page"""
        self.aweme_id: str = aweme_id

        response: Response = self.__session.get(
            f'{self.API_URL}/comment/list/',
            params={
                'aid': 1988,
                'aweme_id': aweme_id,
                'count': size,
                'cursor': (page - 1) * size
            }
        )

        data: Dict[str, Any] = jmespath.search(    
            """
            {
                caption: comments[0].share_info.title,
                video_url: comments[0].share_info.url,
                comments: comments,
                has_more: has_more
            }
            """,
            response.json()
        )

        return Comments(
            comments=[
                self.__parse_comment(comment) 
                for comment in data.get('comments', [])
            ],
            caption=data.get('caption', ''),
            video_url=data.get('video_url', ''),
            has_more=data.get('has_more', False)
        )
    
    def __call__(self, aweme_id: str) -> Comments:
        """Make the class callable"""
        return self.get_all_comments(aweme_id=aweme_id)

def read_ids_from_csv(filename: str) -> List[str]:
    """Read aweme_ids from CSV file"""
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

@click.command(help='TikTok Comment Scraper')
@click.version_option(version='2.0.0', prog_name='TikTok Comment Scraper')
@click.option(
    "--input-file",
    default='urls.csv',
    help='Input CSV file with TikTok video IDs'
)
@click.option(
    "--output",
    default='data/tiktok/all_comments.csv',
    help='Output file for all comments'
)
def main(input_file: str, output: str):
    """Main function to run the TikTok comment scraper"""
    aweme_ids = read_ids_from_csv(input_file)

    if not aweme_ids:
        logger.error(f"No aweme_ids found in {input_file}. Stopping script.")
        return
    
    all_comments_data = []
    scraper = TiktokComment()

    for aweme_id in aweme_ids:
        logger.info(f'Starting scrape for video ID: {aweme_id}')

        try:
            comments: Comments = scraper(aweme_id=aweme_id)
            comment_list = comments.dict['comments']
            
            # Add aweme_id column to each comment
            for comment in comment_list:
                comment['aweme_id'] = aweme_id
                all_comments_data.append(comment)
            
            logger.info(f"Successfully got {len(comment_list)} comments from ID {aweme_id}")

        except Exception as e:
            logger.error(f"Failed to get comments from ID {aweme_id}: {e}")
            continue

    # Save to CSV file
    if not all_comments_data:
        logger.warning('No comments were successfully retrieved to save.')
        return

    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Get column names (header)
    fieldnames = all_comments_data[0].keys()
    
    with open(output, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_comments_data)

    logger.info(f'All comments successfully saved to {output}')

if __name__ == '__main__':
    main()
