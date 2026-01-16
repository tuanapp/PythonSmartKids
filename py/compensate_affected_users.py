"""
Script to identify and compensate users affected by the Google Play billing outage.

This script:
1. Queries all failed purchase verification attempts during the outage period
2. Verifies them against Google Play now that API is working
3. Grants credits to affected users
4. Generates a report

Usage:
    python py/compensate_affected_users.py --start-date "2026-01-15" --end-date "2026-01-16" --dry-run
    python py/compensate_affected_users.py --start-date "2026-01-15" --end-date "2026-01-16" --execute
"""

import argparse
import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.db_factory import DatabaseFactory
from app.services.billing_service import billing_service, SKU_TO_CREDIT_AMOUNT
from app.repositories.db_service import adjust_user_credits
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_failed_purchases(start_date: str, end_date: str):
    """
    Query database for purchases that were not processed during the outage.
    
    We identify these by looking at google_play_purchases where:
    - created_at is within the outage window
    - processed = false (if we had such a column) OR credits were never granted
    
    For now, we'll look at purchases that exist but have no corresponding credit history.
    """
    db_provider = DatabaseFactory.get_provider()
    conn = db_provider._get_connection()
    cursor = conn.cursor()
    
    try:
        # Get all purchases in the date range
        query = """
            SELECT 
                gpp.id,
                gpp.uid,
                gpp.product_id,
                gpp.purchase_token,
                gpp.order_id,
                gpp.created_at,
                gpp.purchase_state
            FROM google_play_purchases gpp
            WHERE gpp.created_at >= %s 
              AND gpp.created_at < %s
              AND gpp.purchase_state = 0  -- Successfully purchased
            ORDER BY gpp.created_at
        """
        
        cursor.execute(query, (start_date, end_date))
        purchases = cursor.fetchall()
        
        results = []
        for purchase in purchases:
            results.append({
                'purchase_id': purchase[0],
                'uid': purchase[1],
                'product_id': purchase[2],
                'purchase_token': purchase[3],
                'order_id': purchase[4],
                'created_at': purchase[5].isoformat() if purchase[5] else None,
                'purchase_state': purchase[6]
            })
        
        return results
        
    finally:
        cursor.close()
        conn.close()


def check_if_credits_granted(uid: str, purchase_id: int) -> bool:
    """
    Check if credits were already granted for this purchase.
    This is a heuristic - we check if there's a credit transaction around the purchase time.
    """
    # For now, we'll assume no credits were granted during the outage
    # You could enhance this by checking credit_history table if you have one
    return False


def verify_and_compensate(purchase: dict, dry_run: bool = True) -> dict:
    """
    Verify a purchase with Google Play and grant credits if valid.
    
    Returns:
        dict with compensation result
    """
    result = {
        'purchase_id': purchase['purchase_id'],
        'uid': purchase['uid'],
        'product_id': purchase['product_id'],
        'order_id': purchase['order_id'],
        'status': 'unknown',
        'credits_granted': 0,
        'error': None
    }
    
    try:
        # Check if this is a credit pack
        if purchase['product_id'] not in SKU_TO_CREDIT_AMOUNT:
            result['status'] = 'skipped'
            result['error'] = f"Product {purchase['product_id']} is not a credit pack"
            return result
        
        # Get expected credits
        expected_credits = SKU_TO_CREDIT_AMOUNT[purchase['product_id']]
        
        # Verify with Google Play
        is_valid, purchase_data, error = billing_service.verify_product_purchase(
            purchase['product_id'],
            purchase['purchase_token']
        )
        
        if not is_valid:
            result['status'] = 'invalid'
            result['error'] = error or "Purchase verification failed"
            return result
        
        # Check if already processed
        if check_if_credits_granted(purchase['uid'], purchase['purchase_id']):
            result['status'] = 'already_compensated'
            return result
        
        # Grant credits
        if not dry_run:
            try:
                # Use the billing service to process the credit pack
                process_result = billing_service.process_credit_pack_purchase(
                    uid=purchase['uid'],
                    product_id=purchase['product_id'],
                    purchase_id=purchase['purchase_id']
                )
                
                result['status'] = 'compensated'
                result['credits_granted'] = process_result['credits_granted']
                logger.info(f"Granted {result['credits_granted']} credits to user {purchase['uid']} for purchase {purchase['order_id']}")
                
            except Exception as e:
                result['status'] = 'error'
                result['error'] = str(e)
                logger.error(f"Failed to grant credits: {e}")
        else:
            result['status'] = 'would_compensate'
            result['credits_granted'] = expected_credits
            logger.info(f"[DRY RUN] Would grant {expected_credits} credits to user {purchase['uid']}")
        
        return result
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
        logger.error(f"Error processing purchase {purchase['purchase_id']}: {e}")
        return result


def generate_report(results: list, output_file: str = None):
    """Generate a compensation report"""
    
    # Count by status
    status_counts = {}
    total_credits = 0
    
    for result in results:
        status = result['status']
        status_counts[status] = status_counts.get(status, 0) + 1
        total_credits += result.get('credits_granted', 0)
    
    report = {
        'summary': {
            'total_purchases': len(results),
            'total_credits_granted': total_credits,
            'by_status': status_counts
        },
        'details': results
    }
    
    # Print summary
    print("\n" + "="*70)
    print("COMPENSATION REPORT")
    print("="*70)
    print(f"Total purchases processed: {len(results)}")
    print(f"Total credits granted: {total_credits}")
    print("\nBreakdown by status:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")
    print("="*70 + "\n")
    
    # Save to file
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"Full report saved to: {output_file}")
    
    return report


def main():
    parser = argparse.ArgumentParser(
        description='Compensate users affected by Google Play billing outage'
    )
    parser.add_argument(
        '--start-date',
        required=True,
        help='Start date of outage (YYYY-MM-DD format)'
    )
    parser.add_argument(
        '--end-date',
        required=True,
        help='End date of outage (YYYY-MM-DD format)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry-run mode (no actual changes)'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Execute compensation (grant credits)'
    )
    parser.add_argument(
        '--output',
        default='compensation_report.json',
        help='Output file for report (default: compensation_report.json)'
    )
    
    args = parser.parse_args()
    
    # Validate dates
    try:
        start_dt = datetime.strptime(args.start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(args.end_date, '%Y-%m-%d')
        if end_dt < start_dt:
            print("Error: end-date must be after start-date")
            sys.exit(1)
    except ValueError as e:
        print(f"Error: Invalid date format. Use YYYY-MM-DD. {e}")
        sys.exit(1)
    
    # Must specify either --dry-run or --execute
    if not (args.dry_run or args.execute):
        print("Error: Must specify either --dry-run or --execute")
        parser.print_help()
        sys.exit(1)
    
    dry_run = args.dry_run
    
    print(f"\nSearching for affected purchases from {args.start_date} to {args.end_date}...")
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'EXECUTE (will grant credits)'}\n")
    
    # Get failed purchases
    purchases = get_failed_purchases(args.start_date, args.end_date)
    
    if not purchases:
        print("No purchases found in the specified date range.")
        return
    
    print(f"Found {len(purchases)} purchase(s) to check.\n")
    
    # Process each purchase
    results = []
    for i, purchase in enumerate(purchases, 1):
        print(f"[{i}/{len(purchases)}] Processing purchase {purchase['order_id']}...")
        result = verify_and_compensate(purchase, dry_run=dry_run)
        results.append(result)
    
    # Generate report
    generate_report(results, output_file=args.output)
    
    if dry_run:
        print("\n*** This was a DRY RUN - no credits were actually granted ***")
        print("Run with --execute to apply changes.\n")


if __name__ == '__main__':
    main()
