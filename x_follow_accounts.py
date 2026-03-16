#!/usr/bin/env python3
"""
X/Twitter Auto-Follow Script
Uses auth_token cookie to follow accounts via X's internal API.
Usage: python3 x_follow_accounts.py [--list FILE] [--dry-run]
"""

import requests
import time
import sys
import argparse

FOLLOW_LIST = "/home/john/Thunderbird/x_osint_follow_list.txt"
AUTH_TOKEN = "d854d7754f8a4a85e5e574dcff3766f098748e80"


def get_ct0_and_session():
    """Get a ct0 token by hitting X API with auth_token cookie."""
    session = requests.Session()
    session.cookies.set("auth_token", AUTH_TOKEN, domain=".x.com")
    session.cookies.set("twid", "u%3D24601273", domain=".x.com")

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
    }

    # Hit API to trigger ct0 cookie generation (401 is expected)
    session.get("https://api.x.com/1.1/account/verify_credentials.json", headers=headers)

    ct0 = session.cookies.get("ct0", domain=".x.com")
    if not ct0:
        ct0 = session.cookies.get("ct0")
    if not ct0:
        print("ERROR: Could not get ct0 token. Auth may be expired.", file=sys.stderr)
        sys.exit(1)

    return ct0, session


def get_user_id(session, ct0, username):
    """Look up a user's numeric ID by screen name."""
    url = "https://x.com/i/api/graphql/xmU6X_CKcnQ5lSrCbAmJsg/UserByScreenName"
    params = {
        "variables": f'{{"screen_name":"{username}","withSafetyModeUserFields":true}}',
        "features": '{"hidden_profile_subscriptions_enabled":true,"profile_label_improvements_pcf_label_in_post_enabled":false,"rweb_tipjar_consumption_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"subscriptions_verification_info_is_identity_verified_enabled":true,"subscriptions_verification_info_verified_since_enabled":true,"highlights_tweets_tab_ui_enabled":true,"responsive_web_twitter_article_notes_tab_enabled":true,"subscriptions_feature_can_gift_premium":true,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"responsive_web_graphql_timeline_navigation_enabled":true}',
    }
    headers = {
        "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
        "x-csrf-token": ct0,
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }

    resp = session.get(url, params=params, headers=headers)
    if resp.status_code != 200:
        return None

    data = resp.json()
    try:
        return data["data"]["user"]["result"]["rest_id"]
    except (KeyError, TypeError):
        return None


def follow_user(session, ct0, user_id):
    """Follow a user by their numeric ID."""
    url = "https://x.com/i/api/1.1/friendships/create.json"
    headers = {
        "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
        "x-csrf-token": ct0,
        "content-type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }
    data = {"user_id": user_id, "include_profile_interstitial_type": 1}

    resp = session.post(url, headers=headers, data=data)
    return resp.status_code == 200


def load_follow_list(path):
    """Load usernames from file (skip comments and blanks)."""
    usernames = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                usernames.append(line)
    return usernames


def main():
    parser = argparse.ArgumentParser(description="Auto-follow X accounts")
    parser.add_argument("--list", default=FOLLOW_LIST, help="Path to follow list file")
    parser.add_argument("--dry-run", action="store_true", help="Just show what would be followed")
    args = parser.parse_args()

    usernames = load_follow_list(args.list)
    print(f"Loaded {len(usernames)} accounts from {args.list}")

    if args.dry_run:
        for u in usernames:
            print(f"  Would follow: @{u}")
        return

    ct0, session = get_ct0_and_session()
    print(f"Got ct0 token, session ready.\n")

    followed = 0
    failed = 0

    for username in usernames:
        user_id = get_user_id(session, ct0, username)
        if not user_id:
            print(f"  SKIP @{username} — could not resolve user ID")
            failed += 1
            continue

        success = follow_user(session, ct0, user_id)
        if success:
            print(f"  ✓ Followed @{username} (ID: {user_id})")
            followed += 1
        else:
            print(f"  ✗ Failed @{username} (ID: {user_id})")
            failed += 1

        time.sleep(2)  # Be polite — don't hammer the API

    print(f"\nDone: {followed} followed, {failed} failed")


if __name__ == "__main__":
    main()
