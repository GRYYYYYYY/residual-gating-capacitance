set flow $::env(STA_FLOW)
set platform $::env(STA_PLATFORM)
foreach lib $::env(STA_LIBS) {read_liberty $lib}
read_db -hier $::env(STA_ODB)
read_sdc $::env(STA_SDC)
set ::env(METAL_OPTION) 5LM_1TM
set ::env(CORNER) TC
if {[file exists $flow/platforms/$platform/derate.tcl]} {source $flow/platforms/$platform/derate.tcl}
source $flow/platforms/$platform/setRC.tcl
set_propagated_clock [all_clocks]
define_process_corner -ext_model_index 0 X
set_extraction_rules_file $::env(DAC_RULES)
set start [clock microseconds]
extract_parasitics
puts "DAC_EXTRACTION_SECONDS [expr {([clock microseconds]-$start)/1000000.0}]"
write_spef $::env(STA_SPEF)
read_spef $::env(STA_SPEF)
report_units
report_worst_slack -max -digits 9
report_wns -max -digits 9
report_tns -max -digits 9
set out $::env(STA_OUT)
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set f [open $out/layout.tsv w]
puts $f "instance\txmin\tymin\txmax\tymax\tmaster"
foreach inst [$block getInsts] {
 set b [$inst getBBox]
 puts $f "[$inst getName]\t[expr {[$b xMin]/double($dbu)}]\t[expr {[$b yMin]/double($dbu)}]\t[expr {[$b xMax]/double($dbu)}]\t[expr {[$b yMax]/double($dbu)}]\t[[$inst getMaster] getName]"
}
close $f
set f [open $out/ports.tsv w]
puts $f "port\tx\ty"
foreach port [$block getBTerms] {
 foreach bp [$port getBPins] {
  foreach box [$bp getBoxes] {
   puts $f "[$port getName]\t[expr {([$box xMin]+[$box xMax])/(2.0*$dbu)}]\t[expr {([$box yMin]+[$box yMax])/(2.0*$dbu)}]"
   break
  }
  break
 }
}
close $f
set f [open $out/bounds.tsv w]
set b [$block getDieArea]
puts $f "[expr {[$b xMin]/double($dbu)}]\t[expr {[$b yMin]/double($dbu)}]\t[expr {[$b xMax]/double($dbu)}]\t[expr {[$b yMax]/double($dbu)}]"
close $f
set f [open $out/endpoints.tsv w]
puts $f "endpoint\tslack"
foreach pin [sta::endpoints] {
 puts $f "[get_full_name $pin]\t[get_property $pin slack_max]"
}
close $f
set paths [find_timing_paths -path_delay max -group_path_count 100000 -endpoint_path_count 1 -unique_paths_to_endpoint -sort_by_slack]
set f [open $out/paths.tsv w]
puts $f "startpoint\tendpoint\tslack\tpins\tnets\tarrivals\trequireds"
foreach p $paths {
 set pins {}; set nets {}; set arrivals {}; set requireds {}
 foreach point [get_property $p points] {
  set pin [get_property $point pin]
  lappend pins [get_full_name $pin]
  set n [get_nets -quiet -of_objects $pin]
  lappend nets [expr {[llength $n] && [lindex $n 0] ne "NULL" ? [get_full_name [lindex $n 0]] : ""}]
  lappend arrivals [get_property $point arrival]
  lappend requireds [get_property $point required]
 }
 puts $f "[get_full_name [get_property $p startpoint]]\t[get_full_name [get_property $p endpoint]]\t[get_property $p slack]\t[join $pins |]\t[join $nets |]\t[join $arrivals |]\t[join $requireds |]"
}
close $f
report_checks -path_delay max -group_path_count 100 -endpoint_path_count 1 -sort_by_slack -format json > $out/top_paths.json
puts "STA_EXPORT_COMPLETE [llength $paths] paths"
exit
