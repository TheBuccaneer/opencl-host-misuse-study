#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import os, csv, time, sys, datetime as dt, requests

GH = "https://api.github.com"
TOKEN = os.getenv("GH_TOKEN", "")
SESSION = requests.Session()
if TOKEN:
    SESSION.headers.update({"Authorization": f"Bearer {TOKEN}"})
SESSION.headers.update({"Accept": "application/vnd.github+json", "User-Agent": "opencl-sampler/2.0"})

TARGET = int(os.getenv("TARGET", "200"))
MONTHS = 12
SIZE_KB_MAX = 200_000
OUT = "projects_sample.csv"

HOST_API_TERMS = ['clEnqueueNDRangeKernel', 'clCreateContext']
BUILD_HINTS = ['CMakeLists.txt', 'Makefile', '.sln', '.vcxproj']

DOMAIN_KEYWORDS = {
    'computer_vision': ['opencv','image','video','vision','camera','face','detection','segmentation','tracking','ocr','stereo'],
    'hpc': ['simulation','scientific','physics','molecular','parallel','mpi','computational','numerical','cluster','supercomputer','sdr','signal-processing'],
    'ml': ['neural','tensorflow','pytorch','cnn','deep','model','training','inference','gan','transformer']
}

reject_stats = {'license':0, 'size':0, 'activity':0, 'host_api_missing':0, 'build_hints_missing':0, 'errors':0}

def rate_guard(resp):
    rem = int(resp.headers.get("X-RateLimit-Remaining", "1"))
    if rem <= 1:
        reset = int(resp.headers.get("X-RateLimit-Reset", "0"))
        wait = max(0, reset - int(time.time()) + 2)
        if wait > 0:
            time.sleep(wait)

def gh_get(url, params=None):
    r = SESSION.get(url, params=params, timeout=30)
    rate_guard(r)
    if r.status_code == 403 and "rate limit" in r.text.lower():
        rate_guard(r)
    r.raise_for_status()
    return r.json()

def search_repos(page=1, per_page=100):
    q = 'OpenCL in:readme language:C language:C++ fork:false archived:false'
    return gh_get(f"{GH}/search/repositories", params={"q": q, "sort": "updated", "order": "desc", "per_page": per_page, "page": page})

def metadata_ok(repo):
    pushed = repo.get("pushed_at") or repo.get("updated_at") or ""
    try:
        pushed_dt = dt.datetime.fromisoformat(pushed.replace("Z",""))
    except Exception:
        reject_stats['activity'] += 1
        return False
    if pushed_dt < dt.datetime.utcnow() - dt.timedelta(days=30*MONTHS):
        reject_stats['activity'] += 1
        return False
    if (repo.get("size") or 0) > SIZE_KB_MAX:
        reject_stats['size'] += 1
        return False
    lic = (repo.get("license") or {}).get("spdx_id") or ""
    if lic in ("NOASSERTION", "NONE", ""):
        reject_stats['license'] += 1
        return False
    return True

def repo_has_host_api_optimized(full_name):
    for term in HOST_API_TERMS:
        try:
            q = f'repo:{full_name} "{term}" language:C language:C++'
            data = gh_get(f"{GH}/search/code", params={"q": q, "per_page": 1})
            time.sleep(6)
            if data.get("total_count", 0) > 0:
                return True
        except Exception:
            time.sleep(6)
            continue
    return False

def repo_has_build_hints(full_name, default_branch):
    try:
        items = gh_get(f"{GH}/repos/{full_name}/contents", params={"ref": default_branch})
        names = {it.get("name","") for it in items if isinstance(it, dict)}
        if any(any(hint.lower() in n.lower() for hint in BUILD_HINTS) for n in names):
            return True
    except Exception:
        pass
    try:
        q = f'repo:{full_name} (filename:CMakeLists.txt OR filename:Makefile OR filename:.sln OR filename:.vcxproj)'
        data = gh_get(f"{GH}/search/code", params={"q": q, "per_page": 1})
        time.sleep(6)
        if data.get("total_count", 0) > 0:
            return True
    except requests.HTTPError as e:
        if e.response.status_code == 422:
            try:
                q = f'repo:{full_name} filename:CMakeLists.txt OR filename:Makefile OR filename:.sln OR filename:.vcxproj'
                data = gh_get(f"{GH}/search/code", params={"q": q, "per_page": 1})
                time.sleep(6)
                if data.get("total_count", 0) > 0:
                    return True
            except requests.HTTPError as e2:
                if e2.response.status_code == 422:
                    for hint in BUILD_HINTS:
                        try:
                            q = f'repo:{full_name} filename:{hint}'
                            data = gh_get(f"{GH}/search/code", params={"q": q, "per_page": 1})
                            time.sleep(6)
                            if data.get("total_count", 0) > 0:
                                return True
                        except Exception:
                            time.sleep(6)
                            continue
                else:
                    time.sleep(6)
        else:
            time.sleep(6)
    except Exception:
        time.sleep(6)
    return False

def get_topics(full_name):
    try:
        headers = {"Accept": "application/vnd.github.mercy-preview+json"}
        if TOKEN:
            headers["Authorization"] = f"Bearer {TOKEN}"
        headers["User-Agent"] = "opencl-sampler/2.0"
        r = SESSION.get(f"{GH}/repos/{full_name}/topics", headers=headers, timeout=30)
        rate_guard(r)
        r.raise_for_status()
        data = r.json()
        return data.get("names", [])
    except Exception:
        return []

def classify_domain_heuristic(repo, topics):
    name = repo.get('name', '').lower()
    desc = repo.get('description', '').lower() if repo.get('description') else ''
    topics_str = ' '.join(topics).lower() if topics else ''
    text = f"{name} {desc} {topics_str}"
    
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        unique_matches = set()
        for kw in keywords:
            if kw in text:
                unique_matches.add(kw)
        scores[domain] = len(unique_matches)
    
    max_score = max(scores.values())
    if max_score == 0:
        return 'other'
    
    priority_order = ['computer_vision', 'hpc', 'ml']
    for domain in priority_order:
        if scores[domain] == max_score:
            return domain
    
    return 'other'

def activity_level(stars, forks):
    if stars > 100 or forks > 50:
        return 'High'
    if stars > 20 or forks > 10:
        return 'Medium'
    return 'Low'

def estimate_loc_via_languages_api(full_name):
    try:
        data = gh_get(f"{GH}/repos/{full_name}/languages")
        bytes_c = data.get('C', 0)
        bytes_cpp = data.get('C++', 0)
        bytes_total = bytes_c + bytes_cpp
        if bytes_total == 0:
            return None
        return int(bytes_total / 70)
    except Exception:
        return None

def write_header_if_needed():
    if not os.path.exists(OUT) or os.path.getsize(OUT) == 0:
        with open(OUT, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["repo","default_branch","stars","forks","domain","language","last_update","is_fork","selected","activity_level","loc"])

def append_repo(repo, domain, act_level, loc):
    with open(OUT, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            repo["full_name"],
            repo.get("default_branch","main"),
            repo.get("stargazers_count",0),
            repo.get("forks_count",0),
            domain,
            repo.get("language",""),
            repo.get("pushed_at") or repo.get("updated_at") or "",
            repo.get("fork", False),
            "",
            act_level,
            loc if loc is not None else ""
        ])

def main():
    write_header_if_needed()
    collected = 0
    seen = set()

    for page in range(1, 21):
        try:
            data = search_repos(page=page, per_page=100)
        except Exception as e:
            reject_stats['errors'] += 1
            continue
        items = data.get("items", [])
        if not items:
            break
        for repo in items:
            full = repo.get("full_name")
            if not full or full in seen:
                continue
            seen.add(full)

            if repo.get("fork") or repo.get("archived"):
                continue
            if not metadata_ok(repo):
                continue

            default_branch = repo.get("default_branch") or "main"

            try:
                if not repo_has_host_api_optimized(full):
                    reject_stats['host_api_missing'] += 1
                    continue
            except Exception:
                reject_stats['errors'] += 1
                continue

            try:
                if not repo_has_build_hints(full, default_branch):
                    reject_stats['build_hints_missing'] += 1
                    continue
            except Exception:
                reject_stats['errors'] += 1
                continue

            topics = get_topics(full)
            domain = classify_domain_heuristic(repo, topics)
            stars = repo.get("stargazers_count", 0)
            forks = repo.get("forks_count", 0)
            act_level = activity_level(stars, forks)
            loc = estimate_loc_via_languages_api(full)

            append_repo(repo, domain, act_level, loc)
            collected += 1
            print(f"[{collected}/{TARGET}] + {full}")
            if collected >= TARGET:
                print(f"\nDone. Wrote {collected} repos to {OUT}")
                print("\nSummary of rejections:")
                for reason, count in reject_stats.items():
                    print(f"  {reason}: {count}")
                return

    print(f"\nFinished with {collected} repos (target {TARGET}).")
    print("\nSummary of rejections:")
    for reason, count in reject_stats.items():
        print(f"  {reason}: {count}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(2)
