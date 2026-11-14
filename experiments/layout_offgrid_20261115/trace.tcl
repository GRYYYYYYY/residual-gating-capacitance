read_db -hier $::env(STA_ODB)
set b [ord::get_db_block]
puts "DAC_DBU [$b getDbUnitsPerMicron]"
set f [open "$::env(STA_SPEF).layers.tsv" w]
puts $f "name\tlayer\twidth\tspacing\tthickness"
foreach layer [[ord::get_db_tech] getLayers] {
 if {[$layer getRoutingLevel] > 0} {puts $f "[$layer getName]\t[$layer getRoutingLevel]\t[$layer getWidth]\t[$layer getSpacing]\tunresolved"}
}
close $f
define_process_corner -ext_model_index 0 X
set_extraction_rules_file $::env(DAC_RULES)
extract_parasitics
write_spef $::env(STA_SPEF)
puts DAC_TRACE_COMPLETE
exit
