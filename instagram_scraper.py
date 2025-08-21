# =================================================================================
# Instagram Comment Scraper - Otomatisasi dari File CSV
# =================================================================================
import os
import sys
import json
import requests
import re
import csv
from loguru import logger
from time import sleep

# Konfigurasi GraphQL
PARENT_QUERY_HASH = "97b41c52301f77ce508f55e66d17620e"
REPLY_QUERY_HASH = "863813fb3a4d6501723f11d1e44a42b1" # Query hash untuk replies
COMMENTS_PER_PAGE = 50

# --- Fungsi Pembantu ---

def read_post_ids_from_csv(filename: str) -> list:
    """Membaca daftar ID post dari file CSV."""
    ids = []
    try:
        with open(filename, 'r', newline='', encoding='utf-8') as csv_file:
            reader = csv.reader(csv_file)
            # Lewati header jika ada
            next(reader, None)
            for row in reader:
                if row and row[0].strip():
                    ids.append(row[0].strip())
    except FileNotFoundError:
        logger.error(f"Error: File '{filename}' tidak ditemukan.")
        return []
    return ids

def build_headers(shortcode: str, cookies_str: str) -> dict:
    """Membangun header HTTP untuk permintaan API."""
    return {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-A125F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "X-Requested-With": "XMLHttpRequest",
        "X-IG-App-ID": "936619743392459",
        "Referer": f"https://www.instagram.com/p/{shortcode}/",
        "Cookie": cookies_str
    }

def graphql_request(query_hash: str, variables: dict, headers: dict) -> dict:
    """Melakukan permintaan GraphQL ke API Instagram."""
    var_str = json.dumps(variables, separators=(",", ":"))
    url = (
        f"https://www.instagram.com/graphql/query/"
        f"?query_hash={query_hash}"
        f"&variables={requests.utils.quote(var_str)}"
    )
    
    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status() # Akan memunculkan HTTPError jika status code 4xx atau 5xx
        return r.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"[!] HTTP error for {query_hash}: {e}")
        return {}

def fetch_replies(shortcode: str, comment_id: str, headers: dict) -> list:
    """Mengambil balasan untuk komentar utama."""
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
                logger.warning(f"Tidak ada balasan ditemukan untuk komentar ID: {comment_id}")
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
            sleep(2) # Jeda untuk menghindari rate limiting
            
    return all_replies

def fetch_comments(shortcode: str, headers: dict) -> list:
    """Mengambil komentar utama dan balasan dari sebuah post."""
    all_comments = []
    has_next = True
    cursor = ""
    
    logger.info(f"Mulai mengambil komentar untuk post {shortcode}...")
    
    while has_next:
        vars = {"shortcode": shortcode, "first": COMMENTS_PER_PAGE}
        if cursor:
            vars["after"] = cursor
            
        data = graphql_request(PARENT_QUERY_HASH, vars, headers)

        # Cek apakah data valid sebelum diproses
        if not data or not data.get("data", {}).get("shortcode_media", {}):
            logger.error(f"Data tidak valid atau permintaan gagal untuk post {shortcode}. Melewatkan.")
            break

        try:
            edge_info = data.get("data", {}).get("shortcode_media", {}).get("edge_media_to_parent_comment", {})
            if not edge_info:
                logger.warning(f"Tidak ada komentar utama ditemukan untuk post {shortcode}")
                break
            
            edges = edge_info.get("edges", [])
            for edge in edges:
                node = edge.get("node", {})
                if node:
                    parent_comment_id = node.get("id")
                    
                    # Tambahkan komentar utama
                    all_comments.append({
                        "post_id": shortcode,
                        "parent_comment_id": parent_comment_id,
                        "comment_id": parent_comment_id,
                        "username": node.get("owner", {}).get("username"),
                        "comment_text": node.get("text"),
                        "created_at": node.get("created_at"),
                        "is_reply": False
                    })
                    
                    # Cek dan ambil balasan jika ada
                    child_comment_count = node.get("edge_threaded_comments", {}).get("count", 0)
                    if child_comment_count > 0:
                        logger.info(f"Mengambil {child_comment_count} balasan untuk komentar ID: {parent_comment_id}")
                        replies = fetch_replies(shortcode, parent_comment_id, headers)
                        all_comments.extend(replies)
            
            page_info = edge_info.get("page_info", {})
            has_next = page_info.get("has_next_page", False)
            cursor = page_info.get("end_cursor", "")
            
        except (KeyError, TypeError) as e:
            logger.error(f"[!] Error parsing data for {shortcode}: {e}")
            break

        if has_next:
            logger.info("Mengambil halaman komentar berikutnya...")
            sleep(2) # Jeda untuk menghindari rate limiting
            
    return all_comments

def main():
    """Fungsi utama untuk menjalankan scraper."""
    # KONFIGURASI COOKIE di sini
    # GANTI DENGAN COOKIE ANDA YANG BARU DAN VALID
    sessionid = "8900711295%3ACOeDeSGecWNZLK%3A9%3AAYf0g_IpxxhTmgjuUWX7Ne8gVjqUAi3KJJRehaD04Q"
    ds_user_id = "8900711295"
    csrftoken = "E5VPI5indmbps5COiHI7DI2LeH7vLA40"
    mid = "aHSP6wALAAEGbmMHO65q6keKTGUT"
    
    cookies_str = f"sessionid={sessionid}; ds_user_id={ds_user_id}; csrftoken={csrftoken}; mid={mid};"
    
    # Baca ID dari file
    ids_to_scrape = read_post_ids_from_csv('instagram_urls.csv')
    
    if not ids_to_scrape:
        logger.error("Tidak ada ID post yang ditemukan di urls.csv.")
        sys.exit(1)
        
    all_comments_data = []

    for post_id in ids_to_scrape:
        logger.info(f"Memproses post ID: {post_id}")
        headers = build_headers(post_id, cookies_str)
        comments = fetch_comments(post_id, headers)
        all_comments_data.extend(comments)

    # Simpan data ke file CSV
    if all_comments_data:
        output_file = 'data/instagram/all_instagram_comments.csv'
        
        # Buat direktori jika belum ada
        output_dir = os.path.dirname(output_file)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Tangani kasus di mana all_comments_data mungkin kosong
        if not all_comments_data:
            logger.warning("Tidak ada komentar yang berhasil diambil untuk disimpan.")
            return

        # Dapatkan semua fieldnames dari semua kamus untuk memastikan tidak ada yang terlewat
        all_keys = set()
        for d in all_comments_data:
            all_keys.update(d.keys())
        fieldnames = sorted(list(all_keys))

        with open(output_file, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_comments_data)
        
        logger.success(f"Berhasil menyimpan {len(all_comments_data)} komentar ke {output_file}")
    else:
        logger.warning("Tidak ada komentar yang berhasil diambil untuk disimpan.")
    
if __name__ == "__main__":
    main()