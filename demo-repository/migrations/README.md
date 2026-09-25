"""
Demo repository — migrations folder.

PLANTED RISK 1: The `priority_score` column added to Order in models.py
has NO migration file here. The migrations folder only contains the
initial schema.

A real project would have:
  versions/001_initial.py
  versions/002_add_priority_score.py  ← THIS IS MISSING

This is what the Database Agent should detect.
"""
