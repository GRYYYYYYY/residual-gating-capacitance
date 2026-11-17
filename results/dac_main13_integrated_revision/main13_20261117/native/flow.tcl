# Same Tcl flow for original and compute-table builds; named stages preserved.
proc measure {name script} {
 set start [clock microseconds]
 uplevel 1 $script
 puts "RUNTIME_STAGE $name [expr {([clock microseconds]-$start)/1000000.0}]"
}
proc rss {name} {
 set f [open /proc/self/status r];set s [read $f];close $f
 regexp {VmRSS:\s+([0-9]+)} $s _ kb
 puts "RUNTIME_RSS $name $kb"
}
set flow $::env(STA_FLOW)
set platform $::env(STA_PLATFORM)
measure layout_and_libs {
 foreach lib $::env(STA_LIBS) {read_liberty $lib}
 read_db -hier $::env(STA_ODB)
 puts "DAC_CT_DBU [[ord::get_db_block] getDbUnitsPerMicron]"
 read_sdc $::env(STA_SDC)
 set ::env(METAL_OPTION) 5LM_1TM
 set ::env(CORNER) TC
 if {[file exists $flow/platforms/$platform/derate.tcl]} {source $flow/platforms/$platform/derate.tcl}
 source $flow/platforms/$platform/setRC.tcl
 set_propagated_clock [all_clocks]
 define_process_corner -ext_model_index 0 X
}
rss before_rule_registration
measure rule_registration {set_extraction_rules_file $::env(DAC_RULES)}
rss after_rule_registration
measure extraction {extract_parasitics}
rss after_extraction
measure spef_write {write_spef $::env(STA_SPEF)}
measure sta_read {read_spef $::env(STA_SPEF)}
measure sta_analysis {
 report_units
 report_worst_slack -max -digits 9
 report_wns -max -digits 9
 report_tns -max -digits 9
}
measure endpoint_export {
 set f [open $::env(STA_OUT)/endpoints.tsv w]
 puts $f "endpoint\tslack"
 foreach pin [sta::endpoints] {puts $f "[get_full_name $pin]\t[get_property $pin slack_max]"}
 close $f
}
puts RUNTIME_COMPLETE
exit
