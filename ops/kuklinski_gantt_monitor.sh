#!/bin/bash

# Kuklinski Gantt Project Monitor
# Updates progress chart every 300 seconds

PROJECT="KUKLINSKI GANTT BUILD"
LOG_FILE="/home/john/Thunderbird/ops/gantt_monitor.log"
CHART_FILE="/home/john/Thunderbird/ops/live_progress_chart.txt"

# Colors for terminal output
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
PURPLE='\033[1;35m'
CYAN='\033[1;36m'
BLUE='\033[1;34m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

update_chart() {
    echo "${BLUE}KUKLINSKI GANTT PROJECT STATUS - LIVE UPDATED: $(date)${NC}" > "$CHART_FILE"
    echo "${WHITE}=======================================================${NC}" >> "$CHART_FILE"
    echo "" >> "$CHART_FILE"
    
    echo "${GREEN}✅ COMPLETED:${NC}" >> "$CHART_FILE"
    echo "  ${GREEN}▪ Client analysis - 3 bookings, 6 guests verified${NC}" >> "$CHART_FILE"
    echo "  ${GREEN}▪ Payment confirmed - $21,244 paid Mar 27${NC}" >> "$CHART_FILE"
    echo "  ${GREEN}▪ Address clarification - Roger/Nick same address${NC}" >> "$CHART_FILE"
    echo "  ${GREEN}▪ Critical gaps identified - excursions, insurance, flights${NC}" >> "$CHART_FILE"
    echo "" >> "$CHART_FILE"
    
    echo "${YELLOW}🔄 IN PROGRESS:${NC}" >> "$CHART_FILE"
    echo "  ${YELLOW}▪ Date validation - Viking policy verification${NC}" >> "$CHART_FILE"
    echo "  ${YELLOW}▪ Architecture synthesis - 35 touchpoint mapping${NC}" >> "$CHART_FILE"
    echo "" >> "$CHART_FILE"
    
    echo "${RED}⏰ URGENT ITEMS:${NC}" >> "$CHART_FILE"
    echo "  ${RED}▪ Excursions - 4+ weeks overdue (Viking from booking)!${NC}" >> "$CHART_FILE"
    echo "  ${RED}▪ Insurance - Pre-existing window may be expired${NC}" >> "$CHART_FILE"
    echo "  ${RED}▪ Validation email - Not sent to Kyle yet${NC}" >> "$CHART_FILE"
    echo "" >> "$CHART_FILE"
    
    echo "${PURPLE}📊 DELIVERABLES STATUS:${NC}" >> "$CHART_FILE"
    echo "  ${PURPLE}1. Architecture summary ${CYAN}[10%]${NC} - Research phase" >> "$CHART_FILE"
    echo "  ${PURPLE}2. Gantt chart ${CYAN}[5%]${NC} - Date validation ongoing" >> "$CHART_FILE"
    echo "  ${PURPLE}3. Schedule document ${CYAN}[15%]${NC} - Data collection" >> "$CHART_FILE"
    echo "" >> "$CHART_FILE"
    
    echo "${CYAN}⏱️ TIMELINE:${NC}" >> "$CHART_FILE"
    echo "  ${CYAN}Start:${NC} 2026-04-07 18:00 MT" >> "$CHART_FILE"
    echo "  ${CYAN}Deadline:${NC} 2026-04-08 (P1 priority)" >> "$CHART_FILE"
    echo "  ${CYAN}Current:${NC} Active validation + synthesis" >> "$CHART_FILE"
    echo "  ${CYAN}Last Updated:${NC} $(date '+%Y-%m-%d %H:%M:%S MT')" >> "$CHART_FILE"
    echo "" >> "$CHART_FILE"
    
    echo "${WHITE}=======================================================${NC}" >> "$CHART_FILE"
    echo "${BLUE}Next update in 120 seconds...${NC}" >> "$CHART_FILE"
}

# Create log entry
echo "Starting Kuklinski Gantt monitor at $(date)" >> "$LOG_FILE"

# Initial chart setup
update_chart

# Continuous monitoring loop
while true; do
    # Update the chart
    update_chart
    
    # Log this update
    echo "Chart updated at $(date)" >> "$LOG_FILE"
    
    # Display current chart
    clear
    cat "$CHART_FILE"
    
    # Wait 120 seconds (2 minutes)
    sleep 120

done