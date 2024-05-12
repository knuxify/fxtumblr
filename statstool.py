#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
Command-line tool to dump statistics.
"""

import argparse
from collections import namedtuple
import datetime

import sqlite3

from fxtumblr import config

STATS_DB = config.get("stats_db", "stats.db")

# Argument parsing
parser = argparse.ArgumentParser(
    prog="statstool.py", description="Tools for parsing fxtumblr instance statistics"
)

subparsers = parser.add_subparsers(title="mode")

plot_parser = subparsers.add_parser("plot")
plot_parser.set_defaults(mode="plot")
plot_parser.add_argument(
    "-d", "--days", type=int, help="How many days back to plot the data for"
)
plot_parser.add_argument(
    "-s", "--start-date", help="Start date (inclusive) for the data (YYYY-MM-DD)"
)
plot_parser.add_argument(
    "-e", "--end-date", help="End date (inclusive) for the data (YYYY-MM-DD)"
)
plot_parser.add_argument(
    "-u",
    "--unique",
    help="Only count unique hits (i.e. multiple hits of the same post are discarded)",
    action="store_true",
)
plot_parser.add_argument(
    "-p",
    "--print-only",
    help="Instead of generating plot, print the data",
    action="store_true",
)

args = parser.parse_args()
try:
    mode = args.mode
except:
    print('No command provided! See "statstool.py --help" for more information.')
    quit(1)

# Plot
if mode == "plot":
    import matplotlib.pyplot as plt

    if not args.days and not args.start_date:
        raise ValueError("Must specify one of --days or --start-date")

    now = datetime.datetime.now().replace(hour=0, minute=0, second=0)

    if args.days:
        start_date = now - datetime.timedelta(days=args.days)
    elif args.start_date:
        start_date = datetime.datetime.strptime(args.start_date, "%Y-%m-%d")

    if args.end_date:
        end_date = datetime.datetime.strptime(args.end_date, "%Y-%m-%d")
    else:
        end_date = now

    if start_date > end_date:
        raise ValueError("Start date is earlier than end date")

    delta = end_date - start_date

    start_date_epoch = int(start_date.strftime("%s"))
    end_date_epoch = int((end_date + datetime.timedelta(days=1)).strftime("%s")) - 1

    hit_tuple = namedtuple("hit_tuple", "id time post modifiers failed")
    hits = []
    data = {}
    with sqlite3.connect(STATS_DB) as db:
        for i in range(delta.days + 1):
            checked_date = start_date + datetime.timedelta(days=i)
            checked_date_start_epoch = int(checked_date.strftime("%s"))
            checked_date_end_epoch = (
                int((checked_date + datetime.timedelta(days=1)).strftime("%s")) - 1
            )

            hits_for_day = []
            posts = set()
            fetch = db.execute(
                f"SELECT * FROM fxtumblr_stats WHERE time BETWEEN {checked_date_start_epoch} AND {checked_date_end_epoch};"
            ).fetchall()
            for hit in fetch:
                hit_parsed = hit_tuple(*hit)._asdict()
                if args.unique and hit_parsed["post"] in posts:
                    continue
                posts.add(hit_parsed["post"])
                hits_for_day.append(hit_parsed)

            data[checked_date.strftime("%Y-%m-%d")] = len(hits_for_day)

    if args.print_only:
        for date, hits in data.items():
            print(f"{date}: {hits} hits")
    else:
        fig, ax = plt.subplots()
        ax.set_xlabel("date")
        ax.set_ylabel("hits")
        ax.plot(list(data.keys()), list(data.values()), linestyle="solid", marker="o")
        for tick in ax.get_xticklabels():
            tick.set_rotation(75)
        fig.savefig("stats.png")

        print("Done! Saved as stats.png")
