 Analyze the attached SPF5000 memory collector TSV and determine whether it shows a real backend memory leak or normal warm-up/cache behavior.
   
   Context:
   - Device: Raspberry Pi 4
   - App: SPF5000
   - The backend process is the Python app; Chromium memory is tracked separately
   - Prior backend leak work already reduced a major issue, so I want you to check whether any leak still remains over this longer run
   - The file may contain stray lines like `RssShmem: 0 kB` between TSV rows; ignore any non-data lines
   - Treat `backend_rssshmem_kb` carefully: in prior runs, `backend_rssanon_kb + backend_rssfile_kb == backend_vmrss_kb`, so do not double-count shared memory if the column appears inconsistent
   
   Columns:
   - epoch
   - iso_utc
   - pid
   - backend_vmrss_kb
   - backend_rssanon_kb
   - backend_rssfile_kb
   - backend_rssshmem_kb
   - backend_vmsize_kb
   - backend_threads
   - chromium_total_rss_kb
   
   Please:
   1. Parse the TSV and ignore malformed/non-data lines
   2. Report sample count and total duration
   3. Compute start, end, min, max, average, net delta, and slope/hour for:
      - backend_vmrss_kb
      - backend_rssanon_kb
      - backend_rssfile_kb
      - chromium_total_rss_kb
   4. Break the run into hourly windows and summarize backend RSS behavior by hour
   5. Identify notable jumps or drops, especially large 5-minute changes
   6. Determine whether the backend trend is:
      - monotonic/unbounded leak,
      - warm-up then mostly flat,
      - stepwise growth with occasional release,
      - or dominated by Chromium/system activity rather than SPF5000
   7. Pay special attention to `backend_rssanon_kb`; explain whether anonymous memory is truly creeping upward
   8. Give a final verdict with confidence level:
      - “likely leak”
      - “possible leak, inconclusive”
      - “likely normal behavior”
   9. If it looks abnormal, suggest the most likely subsystem to inspect next and the most useful next instrumentation to add
   
   Return the answer in plain English with concrete numbers, not just general impressions.