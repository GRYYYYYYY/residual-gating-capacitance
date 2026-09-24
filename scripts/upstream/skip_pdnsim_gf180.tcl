# GF180's zero-resistance power vias make optional PDNSim analysis fail.
# Signal SPEF/STA auditing does not modify these PDK values or run IR analysis.
unset -nocomplain ::env(PWR_NETS_VOLTAGES) ::env(GND_NETS_VOLTAGES)
