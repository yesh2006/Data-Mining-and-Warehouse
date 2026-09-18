# Task B: verify three idempotent runs
Import-Csv ".\staging\manifests\load_runs.csv" |
    Where-Object {$_.run_label -in @("proof1","proof2","proof3")} |
    Select-Object run_label, rows, checksum |
    Format-Table -AutoSize
