#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import pandas as pd
import sys

INPUT_CSV = "projects_sample.csv"
OUTPUT_CSV = "projects_pilot_50.csv"
TARGET_TOTAL = 50
RANDOM_STATE = 42

DOMAIN_QUOTAS = {
    'computer_vision': 15,
    'hpc': 15,
    'ml': 15,
    'other': 5
}

ACTIVITY_LEVELS = ['High', 'Medium', 'Low']

def main():
    df = pd.read_csv(INPUT_CSV)
    df['selected'] = 0
    
    df = df[df['is_fork'] == False].copy()
    
    df['domain'] = df['domain'].str.lower()
    valid_domains = set(DOMAIN_QUOTAS.keys())
    df.loc[~df['domain'].isin(valid_domains), 'domain'] = 'other'
    
    invalid_activity = df[~df['activity_level'].isin(ACTIVITY_LEVELS)]
    if not invalid_activity.empty:
        print(f"Warning: {len(invalid_activity)} repos with invalid activity_level, setting to 'Low'")
        df.loc[~df['activity_level'].isin(ACTIVITY_LEVELS), 'activity_level'] = 'Low'
    
    selected_indices = []
    domain_stats = {}
    
    for domain, target in DOMAIN_QUOTAS.items():
        domain_df = df[df['domain'] == domain].copy()
        available = len(domain_df)
        
        if available < target:
            print(f"Warning: {domain} has only {available} repos (target: {target})")
            selected_from_domain = domain_df.index.tolist()
            domain_stats[domain] = {'target': target, 'actual': available, 'shortage': target - available}
        else:
            activity_target = {
                15: {'High': 5, 'Medium': 5, 'Low': 5},
                5: {'High': 2, 'Medium': 2, 'Low': 1}
            }.get(target, {'High': target // 3, 'Medium': target // 3, 'Low': target - 2 * (target // 3)})
            
            selected_from_domain = []
            remaining_target = target
            
            for activity in ACTIVITY_LEVELS:
                activity_df = domain_df[domain_df['activity_level'] == activity]
                activity_available = len(activity_df)
                activity_need = activity_target.get(activity, 0)
                
                if activity_available >= activity_need:
                    sampled = activity_df.sample(n=activity_need, random_state=RANDOM_STATE)
                    selected_from_domain.extend(sampled.index.tolist())
                    remaining_target -= activity_need
                else:
                    selected_from_domain.extend(activity_df.index.tolist())
                    remaining_target -= activity_available
                
                domain_df = domain_df.drop(activity_df.index, errors='ignore')
            
            if remaining_target > 0 and len(domain_df) > 0:
                additional = domain_df.sample(n=min(remaining_target, len(domain_df)), random_state=RANDOM_STATE)
                selected_from_domain.extend(additional.index.tolist())
            
            domain_stats[domain] = {'target': target, 'actual': len(selected_from_domain), 'shortage': 0}
        
        selected_indices.extend(selected_from_domain)
    
    total_selected = len(selected_indices)
    shortage_total = TARGET_TOTAL - total_selected
    
    if shortage_total > 0:
        print(f"Warning: Total shortage of {shortage_total} repos, filling from domains with surplus")
        remaining_df = df[~df.index.isin(selected_indices)].copy()
        
        if len(remaining_df) >= shortage_total:
            additional = remaining_df.sample(n=shortage_total, random_state=RANDOM_STATE)
            selected_indices.extend(additional.index.tolist())
        else:
            selected_indices.extend(remaining_df.index.tolist())
            print(f"Error: Not enough repos to reach target of {TARGET_TOTAL}. Only {len(selected_indices)} available.")
    
    df.loc[selected_indices, 'selected'] = 1
    df.to_csv(OUTPUT_CSV, index=False)
    
    selected_df = df[df['selected'] == 1]
    
    print("\n" + "=" * 60)
    print("PILOT SAMPLE SUMMARY (50 repos)")
    print("=" * 60)
    
    ct = pd.crosstab(selected_df['domain'], selected_df['activity_level'], margins=True)
    if 'High' not in ct.columns:
        ct['High'] = 0
    if 'Medium' not in ct.columns:
        ct['Medium'] = 0
    if 'Low' not in ct.columns:
        ct['Low'] = 0
    ct = ct[['High', 'Medium', 'Low', 'All']]
    print("\nDomain × Activity:")
    print(ct)
    
    print("\nDomain totals:")
    for domain, stats in domain_stats.items():
        if stats['shortage'] > 0:
            print(f"  {domain}: {stats['actual']} (target: {stats['target']}, shortage: {stats['shortage']})")
        else:
            print(f"  {domain}: {stats['actual']} (target: {stats['target']})")
    
    print(f"\nTotal selected: {len(selected_df)}")
    print(f"Output written to: {OUTPUT_CSV}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)