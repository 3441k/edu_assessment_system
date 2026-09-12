#!/usr/bin/env python3
"""Simulate many students taking a test against a running server.

Hybrid-autosave style load (lighter than old 30s full sync):
  - one answer save when starting
  - periodic single-question saves every 90s
  - batch save + submit at the end

Usage:
  1. Start server: ./run_server_production.py
  2. Ensure test exists with questions; students stress1..stressN exist (or use --create-students)
  3. Run:
       python scripts/stress_test.py --test-id 1 --users 15

Example with custom URL and passwords:
       python scripts/stress_test.py --base-url http://127.0.0.1:5000 --test-id 1 \\
           --users 15 --username-prefix stress --password secret123
"""

import argparse
import concurrent.futures
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests


def login(session, base_url, username, password):
    r = session.post(
        f"{base_url}/api/v1/auth/login",
        json={"username": username, "password": password},
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Login failed for {username}: {r.status_code} {r.text[:200]}")
    if r.json().get("user", {}).get("role") != "student":
        raise RuntimeError(f"{username} is not a student account")


def lecturer_session(base_url, lecturer_user, lecturer_pass):
    lect = requests.Session()
    lr = lect.post(
        f"{base_url}/api/v1/auth/login",
        json={"username": lecturer_user, "password": lecturer_pass},
        timeout=30,
    )
    if lr.status_code != 200:
        raise RuntimeError("Lecturer/admin login failed")
    return lect


def create_student_via_register(base_url, username, password, lecturer_user, lecturer_pass):
    """Register student using lecturer session (setup helper)."""
    lect = lecturer_session(base_url, lecturer_user, lecturer_pass)
    sr = lect.post(
        f"{base_url}/api/v1/auth/register",
        json={"username": username, "password": password, "student_id": username.upper()},
        timeout=30,
    )
    if sr.status_code not in (200, 201):
        if "already exists" in sr.text:
            return
        raise RuntimeError(f"Register {username} failed: {sr.status_code} {sr.text[:200]}")


def reset_stress_attempts(base_url, test_id, usernames, lecturer_user, lecturer_pass):
    """Delete stress students' submissions for this test so they can start again."""
    lect = lecturer_session(base_url, lecturer_user, lecturer_pass)
    names = set(usernames)
    sr = lect.get(f"{base_url}/api/v1/submissions?test_id={test_id}", timeout=30)
    if sr.status_code != 200:
        raise RuntimeError(f"Could not list submissions: {sr.status_code} {sr.text[:200]}")
    reset_count = 0
    for item in sr.json():
        if item.get("username") not in names:
            continue
        rr = lect.post(f"{base_url}/api/v1/submissions/{item['id']}/reset", timeout=30)
        if rr.status_code != 200:
            raise RuntimeError(f"Reset {item.get('username')} failed: {rr.status_code} {rr.text[:200]}")
        reset_count += 1
    print(f"Reset {reset_count} previous stress submissions for test {test_id}.")


def student_run(base_url, username, password, test_id, duration_sec, sync_interval_sec):
    session = requests.Session()
    t0 = time.time()
    stats = {"username": username, "errors": [], "saves": 0, "submitted": False}

    try:
        login(session, base_url, username, password)

        tr = session.get(f"{base_url}/api/v1/tests/{test_id}", timeout=30)
        if tr.status_code != 200:
            raise RuntimeError(f"Load test failed: {tr.status_code}")
        test = tr.json()
        questions = test.get("questions") or []
        if not questions:
            raise RuntimeError("Test has no questions")

        existing = session.get(
            f"{base_url}/api/v1/submissions?test_id={test_id}",
            timeout=30,
        )
        submission_id = None
        if existing.status_code == 200:
            in_progress = next(
                (s for s in existing.json() if s.get("status") == "in_progress"),
                None,
            )
            if in_progress:
                submission_id = in_progress["id"]

        if submission_id is None:
            sr = session.post(
                f"{base_url}/api/v1/submissions",
                json={"test_id": test_id},
                timeout=30,
            )
            if sr.status_code not in (200, 201):
                raise RuntimeError(f"Create submission failed: {sr.status_code} {sr.text[:200]}")
            submission_id = sr.json()["id"]

        q_index = 0
        last_nav_save = time.time()
        last_periodic_sync = time.time()

        while time.time() - t0 < duration_sec:
            now = time.time()
            question = questions[q_index % len(questions)]
            payload = {
                "question_id": question["id"],
                "answer_text": f"Stress answer from {username} q{question['id']} t{int(now)}",
            }

            # Simulate hybrid: server write when changing question (~every 20s)
            if now - last_nav_save >= 20:
                ar = session.post(
                    f"{base_url}/api/v1/submissions/{submission_id}/answers",
                    json=payload,
                    timeout=30,
                )
                if ar.status_code == 200:
                    stats["saves"] += 1
                else:
                    stats["errors"].append(f"nav_save:{ar.status_code}")
                q_index += 1
                last_nav_save = now

            # Simulate hybrid: periodic sync of current question (~every 90s)
            elif now - last_periodic_sync >= sync_interval_sec:
                ar = session.post(
                    f"{base_url}/api/v1/submissions/{submission_id}/answers",
                    json=payload,
                    timeout=30,
                )
                if ar.status_code == 200:
                    stats["saves"] += 1
                else:
                    stats["errors"].append(f"periodic_save:{ar.status_code}")
                last_periodic_sync = now

            time.sleep(2)

        answers = []
        for q in questions:
            answers.append({
                "question_id": q["id"],
                "answer_text": f"Final batch from {username} on q{q['id']}",
            })
        br = session.post(
            f"{base_url}/api/v1/submissions/{submission_id}/answers/batch",
            json={"answers": answers},
            timeout=60,
        )
        if br.status_code != 200:
            stats["errors"].append(f"batch:{br.status_code}")
        else:
            stats["saves"] += 1

        sub = session.post(
            f"{base_url}/api/v1/submissions/{submission_id}/submit",
            timeout=30,
        )
        if sub.status_code == 200:
            stats["submitted"] = True
        else:
            stats["errors"].append(f"submit:{sub.status_code}")

    except Exception as exc:
        stats["errors"].append(str(exc))

    stats["elapsed_sec"] = round(time.time() - t0, 2)
    return stats


def main():
    parser = argparse.ArgumentParser(description="Stress-test student test-taking load")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--test-id", type=int, required=True)
    parser.add_argument("--users", type=int, default=15)
    parser.add_argument("--username-prefix", default="stress")
    parser.add_argument("--password", default="stress123")
    parser.add_argument("--duration", type=int, default=120, help="Seconds each virtual student runs")
    parser.add_argument("--sync-interval", type=int, default=90, help="Match hybrid server sync interval")
    parser.add_argument("--create-students", action="store_true", help="Create stress users via lecturer API")
    parser.add_argument(
        "--reset-attempts",
        action="store_true",
        help="Reset stress students' submissions for this test so they can retake it",
    )
    parser.add_argument("--lecturer-user", default="admin")
    parser.add_argument("--lecturer-password", default="admin")
    args = parser.parse_args()

    usernames = [f"{args.username_prefix}{i}" for i in range(1, args.users + 1)]

    if args.create_students:
        print("Creating student accounts...")
        for name in usernames:
            create_student_via_register(
                args.base_url, name, args.password,
                args.lecturer_user, args.lecturer_password,
            )
        print(f"Ensured {len(usernames)} student accounts exist.")

    if args.reset_attempts:
        reset_stress_attempts(
            args.base_url,
            args.test_id,
            usernames,
            args.lecturer_user,
            args.lecturer_password,
        )

    print(f"Stress test: {args.users} users, test_id={args.test_id}, {args.duration}s each")
    print(f"Target: {args.base_url}")
    print("Use run_server_production.py for realistic classroom load.\n")

    started = time.time()
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.users) as pool:
        futures = [
            pool.submit(
                student_run,
                args.base_url,
                name,
                args.password,
                args.test_id,
                args.duration,
                args.sync_interval,
            )
            for name in usernames
        ]
        for fut in concurrent.futures.as_completed(futures):
            results.append(fut.result())

    elapsed = round(time.time() - started, 2)
    ok = sum(1 for r in results if r["submitted"] and not r["errors"])
    failed = len(results) - ok
    total_saves = sum(r["saves"] for r in results)

    print(f"\nDone in {elapsed}s — submitted OK: {ok}/{len(results)}, failed: {failed}")
    print(f"Total answer saves (approx): {total_saves}")
    for r in sorted(results, key=lambda x: x["username"]):
        status = "OK" if r["submitted"] and not r["errors"] else "FAIL"
        err = "; ".join(r["errors"][:3]) if r["errors"] else ""
        print(f"  {r['username']}: {status} saves={r['saves']} {err}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
