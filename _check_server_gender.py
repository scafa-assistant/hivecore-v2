#!/usr/bin/env python3
"""
Check ALL 6 EGON agents on the server for gender assignments.
Connects via SSH, reads DNA/brain files and state.yaml for each agent.
Research script - read only.
"""

import paramiko
import sys

HOST = "159.69.157.42"
USER = "root"
PASSWORD = "$7pa+12+67kR#rPK$7pah"
EGON_DIR = "/opt/hivecore-v2/egons/"

AGENTS = {
    "adam_001":   {"brain": "v1", "dna_file": "soul.md"},
    "eva_002":    {"brain": "v2", "dna_file": "core/dna.md"},
    "lilith_003": {"brain": "v2", "dna_file": "core/dna.md"},
    "kain_004":   {"brain": "v2", "dna_file": "core/dna.md"},
    "ada_005":    {"brain": "v2", "dna_file": "core/dna.md"},
    "abel_006":   {"brain": "v2", "dna_file": "core/dna.md"},
}

SEARCH_TERMS = ["geschlecht", "gender", "weiblich", "männlich", "frau", "mann", "male", "female"]


def ssh_exec(client, cmd):
    """Execute command via SSH and return stdout."""
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return out, err


def read_remote_file(client, path):
    """Read a file from the remote server. Returns content or error string."""
    out, err = ssh_exec(client, f"cat '{path}' 2>&1")
    return out


def search_in_content(content, label=""):
    """Search for gender-related terms in content. Returns list of matches."""
    matches = []
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        for term in SEARCH_TERMS:
            if term.lower() in line_lower:
                matches.append((i, term, line.strip()))
    return matches


def main():
    print("=" * 80)
    print("EGON Server Gender Assignment Check")
    print(f"Server: {HOST}")
    print("=" * 80)
    print()

    # Connect
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Connecting to {HOST}...")
        client.connect(HOST, username=USER, password=PASSWORD, timeout=15)
        print("Connected successfully.\n")
    except Exception as e:
        print(f"CONNECTION FAILED: {e}")
        sys.exit(1)

    # Step 1: Get full directory structure
    print("=" * 80)
    print("STEP 1: Full file structure on server")
    print("=" * 80)
    out, err = ssh_exec(client, 
        f"find {EGON_DIR} -name '*.md' -o -name '*.yaml' -o -name '*.yml' | sort | head -150")
    print(out)
    if err:
        print(f"[STDERR]: {err}")
    print()

    # Step 2: Check each agent
    print("=" * 80)
    print("STEP 2: Per-Agent Gender Analysis")
    print("=" * 80)
    
    summary = {}

    for agent_name, info in AGENTS.items():
        print()
        print("-" * 70)
        print(f"AGENT: {agent_name} (Brain: {info['brain']})")
        print("-" * 70)
        
        agent_dir = f"{EGON_DIR}{agent_name}/"
        dna_path = f"{agent_dir}{info['dna_file']}"
        state_path = f"{agent_dir}core/state.yaml"
        
        agent_matches = []
        
        # 2a: Read DNA file
        print(f"\n  [DNA] Reading: {dna_path}")
        dna_content = read_remote_file(client, dna_path)
        
        if "No such file" in dna_content or not dna_content.strip():
            print(f"  [DNA] FILE NOT FOUND or EMPTY")
        else:
            print(f"  [DNA] File size: {len(dna_content)} bytes")
            matches = search_in_content(dna_content, "DNA")
            if matches:
                print(f"  [DNA] FOUND {len(matches)} gender-related lines:")
                for line_num, term, line_text in matches:
                    print(f"         Line {line_num} (term: '{term}'): {line_text[:120]}")
                    agent_matches.append(("DNA", line_num, term, line_text))
            else:
                print(f"  [DNA] No gender-related terms found.")
            
            # Print first 30 lines for context
            lines = dna_content.split("\n")[:30]
            print(f"\n  [DNA] First 30 lines:")
            for i, l in enumerate(lines, 1):
                print(f"    {i:3d} | {l}")
        
        # 2b: Read state.yaml
        print(f"\n  [STATE] Reading: {state_path}")
        state_content = read_remote_file(client, state_path)
        
        if "No such file" in state_content or not state_content.strip():
            print(f"  [STATE] FILE NOT FOUND or EMPTY")
        else:
            print(f"  [STATE] File size: {len(state_content)} bytes")
            matches = search_in_content(state_content, "STATE")
            if matches:
                print(f"  [STATE] FOUND {len(matches)} gender-related lines:")
                for line_num, term, line_text in matches:
                    print(f"           Line {line_num} (term: '{term}'): {line_text[:120]}")
                    agent_matches.append(("STATE", line_num, term, line_text))
            else:
                print(f"  [STATE] No gender-related terms found.")
            
            # Print full state.yaml (usually short)
            print(f"\n  [STATE] Full content:")
            for i, l in enumerate(state_content.split("\n"), 1):
                print(f"    {i:3d} | {l}")
        
        # 2c: Also check if there is a soul.md for v2 agents (just in case)
        if info["brain"] == "v2":
            soul_path = f"{agent_dir}soul.md"
            print(f"\n  [EXTRA] Checking if soul.md exists: {soul_path}")
            soul_content = read_remote_file(client, soul_path)
            if "No such file" not in soul_content and soul_content.strip():
                print(f"  [EXTRA] soul.md EXISTS ({len(soul_content)} bytes)")
                matches = search_in_content(soul_content, "SOUL")
                if matches:
                    for line_num, term, line_text in matches:
                        print(f"           Line {line_num} (term: '{term}'): {line_text[:120]}")
                        agent_matches.append(("SOUL.MD", line_num, term, line_text))
            else:
                print(f"  [EXTRA] No soul.md (expected for v2)")
        
        summary[agent_name] = agent_matches

    # Step 3: Summary
    print()
    print("=" * 80)
    print("STEP 3: SUMMARY")
    print("=" * 80)
    print()
    print(f"{'Agent':<15} {'Brain':<5} {'Gender Matches':<10} {'Details'}")
    print("-" * 80)
    for agent_name, info in AGENTS.items():
        matches = summary.get(agent_name, [])
        if matches:
            details = "; ".join([f"{src}:{term}='{txt[:50]}'" for src, ln, term, txt in matches[:3]])
        else:
            details = "No gender terms found"
        print(f"{agent_name:<15} {info['brain']:<5} {len(matches):<10} {details}")
    
    print()
    print("Done.")
    client.close()


if __name__ == "__main__":
    main()
