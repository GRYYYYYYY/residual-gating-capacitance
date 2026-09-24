# ORFS PRE_FINAL_REPORT_TCL hook: time extraction without changing arguments.
rename extract_parasitics openrcbench_original_extract_parasitics
proc extract_parasitics {args} {
    set start [clock microseconds]
    set code [catch {uplevel 1 [list openrcbench_original_extract_parasitics {*}$args]} result options]
    set seconds [expr {([clock microseconds] - $start) / 1000000.0}]
    puts [format "OPENRCBENCH_EXTRACTION_SECONDS %.6f" $seconds]
    return -options $options $result
}
