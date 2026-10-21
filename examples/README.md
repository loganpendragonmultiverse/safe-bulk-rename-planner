# Disposable rename example

Create a new empty folder and two synthetic text files named `chapter 01.txt` and `chapter 02.txt`. From outside that folder:

```bash
rename-plan ./demo --match ' ' --replace '-' --output plan.json --html review.html
rename-plan --apply-manifest plan.json
rename-plan --inspect-recovery plan.json.journal.json
rename-plan --undo plan.json
```

Review the manifest or download a selected manifest from the HTML before applying. Existing output/journal names are refused; choose new names for later runs. Verify exact original names and bytes after undo. Do not test on important files or treat this as post-crash automatic recovery. On Windows the same commands use the console entry point installed by pip; use your shell's normal quoting for paths.
