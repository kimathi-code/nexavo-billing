# 2026-09-23 04:18:23 by RouterOS 7.22.3
# software id = BK1P-CI7R
#
# model = CCR2004-16G-2S+
# serial number = HMM0B37CYVQ
/interface bridge
add admin-mac=D0:EA:11:CC:59:15 auto-mac=no comment=defconf name=bridge \
    vlan-filtering=yes
/interface ethernet
set [ find default-name=ether1 ] comment="WAN1 - Copper Alternative"
set [ find default-name=ether2 ] comment="WAN2 - Copper Alternative"
set [ find default-name=ether3 ] comment="WORKPLACE - RB951"
set [ find default-name=ether4 ] comment="WAN - ZUKU"
set [ find default-name=ether5 ] comment="OLT - V-SOL EPON"
set [ find default-name=ether6 ] comment="OLT - Management"
set [ find default-name=ether7 ] comment="MGMT - Current Access"
set [ find default-name=ether8 ] comment="LAN - Distribution"
set [ find default-name=ether9 ] comment="LAN - Distribution"
set [ find default-name=ether10 ] comment="LAN - Distribution"
set [ find default-name=ether11 ] comment="LAN - Distribution"
set [ find default-name=ether12 ] comment="LAN - Distribution"
set [ find default-name=ether13 ] comment="LAN - Distribution"
set [ find default-name=ether14 ] comment="LAN - Distribution"
set [ find default-name=ether15 ] comment="LAN - Distribution"
set [ find default-name=ether16 ] comment="LAN - Distribution"
set [ find default-name=sfp-sfpplus1 ] comment="WAN1 - SFP+"
set [ find default-name=sfp-sfpplus2 ] comment="WAN2 - SFP+"
/interface vlan
add comment="NEXAVO Management VLAN" interface=bridge name=vlan10-mgmt \
    vlan-id=10
add comment="NEXAVO OLT Management VLAN" interface=bridge name=\
    vlan20-olt-mgmt vlan-id=20
add comment="NEXAVO Infrastructure VLAN" interface=bridge name=vlan30-infra \
    vlan-id=30
add comment="PPPoE Service VLAN" interface=bridge name=vlan40-pppoe vlan-id=\
    40
add comment="IPoE Service VLAN" interface=bridge name=vlan50-ipoe vlan-id=50
add comment="Static Service VLAN" interface=bridge name=vlan60-static \
    vlan-id=60
add comment="Hotspot Service VLAN" interface=bridge name=vlan70-hotspot \
    vlan-id=70
/interface list
add comment="NEXAVO WAN Interfaces" name=WAN
add comment="NEXAVO Internal Interfaces" name=LAN
add comment="NEXAVO Subscriber Services" name=SUBSCRIBERS
/interface bridge port
add bridge=bridge comment="NEXAVO Management Access" frame-types=\
    admit-only-untagged-and-priority-tagged interface=ether7 pvid=10
add bridge=bridge comment="OLT Management Access" frame-types=\
    admit-only-untagged-and-priority-tagged interface=ether6 pvid=20
add bridge=bridge comment="OLT Service Trunk" frame-types=\
    admit-only-vlan-tagged interface=ether5
/interface bridge vlan
add bridge=bridge comment="NEXAVO Management VLAN 10" tagged=bridge untagged=\
    ether7 vlan-ids=10
add bridge=bridge comment="NEXAVO OLT Management VLAN 20" tagged=bridge \
    untagged=ether6 vlan-ids=20
add bridge=bridge comment="PPPoE Service VLAN" tagged=bridge,ether5 vlan-ids=\
    40
add bridge=bridge comment="IPoE Service VLAN" tagged=bridge,ether5 vlan-ids=\
    50
add bridge=bridge comment="Static Service VLAN" tagged=bridge,ether5 \
    vlan-ids=60
add bridge=bridge comment="Hotspot Service VLAN" tagged=bridge,ether5 \
    vlan-ids=70
/interface list member
add interface=ether3 list=WAN
add interface=ether4 list=WAN
add interface=vlan10-mgmt list=LAN
add interface=vlan20-olt-mgmt list=LAN
add interface=vlan30-infra list=LAN
add interface=vlan40-pppoe list=LAN
add interface=vlan50-ipoe list=LAN
add interface=vlan60-static list=LAN
add interface=vlan70-hotspot list=LAN
add interface=vlan40-pppoe list=SUBSCRIBERS
add interface=vlan50-ipoe list=SUBSCRIBERS
add interface=vlan60-static list=SUBSCRIBERS
add interface=vlan70-hotspot list=SUBSCRIBERS
/ip address
add address=10.10.10.1/24 comment="NEXAVO Management Gateway" interface=\
    vlan10-mgmt network=10.10.10.0
add address=10.10.20.1/24 comment="NEXAVO OLT Management Gateway" interface=\
    vlan20-olt-mgmt network=10.10.20.0
add address=192.168.7.2/24 comment="WAN1 - Workplace" interface=ether3 \
    network=192.168.7.0
add address=10.40.0.1/16 comment="PPPoE Gateway" interface=vlan40-pppoe \
    network=10.40.0.0
add address=10.50.0.1/16 comment="IPoE Gateway" interface=vlan50-ipoe \
    network=10.50.0.0
add address=10.60.0.1/16 comment="Static Service Gateway" interface=\
    vlan60-static network=10.60.0.0
add address=10.70.0.1/16 comment="Hotspot Gateway" interface=vlan70-hotspot \
    network=10.70.0.0
add address=10.10.30.1/24 comment="NEXAVO Infrastructure Gateway" interface=\
    vlan30-infra network=10.10.30.0
/ip dhcp-client
add comment="WAN2 - ZUKU DHCP" default-route-distance=2 dhcp-options=hostname \
    interface=ether4 name=client1
/ip firewall filter
add action=accept chain=forward comment=\
    "FORWARD - Allow established and related" connection-state=\
    established,related
add action=accept chain=input comment="INPUT - Allow established and related" \
    connection-state=established,related
add action=drop chain=forward comment="FORWARD - Drop invalid" \
    connection-state=invalid
add action=drop chain=input comment="INPUT - Drop invalid" connection-state=\
    invalid
add action=accept chain=input comment="INPUT - Management VLAN" src-address=\
    10.10.10.0/24
add action=accept chain=input comment="INPUT - OLT Management VLAN" \
    src-address=10.10.20.0/24
add action=accept chain=input comment="INPUT - Infrastructure VLAN" \
    src-address=10.10.30.0/24
add action=drop chain=input comment="INPUT - Drop unsolicited WAN traffic" \
    in-interface-list=WAN
add action=accept chain=input comment="INPUT - IPoE DHCP" dst-port=67 \
    protocol=udp src-address=10.50.0.0/16
add action=accept chain=input comment="INPUT - Hotspot DHCP" dst-port=67 \
    protocol=udp src-address=10.70.0.0/16
add action=drop chain=input comment="INPUT - Drop everything else"
add action=accept chain=forward comment="FORWARD - Management VLAN" \
    in-interface=vlan10-mgmt
add action=accept chain=forward comment="FORWARD - Subscribers to Internet" \
    in-interface-list=SUBSCRIBERS out-interface-list=WAN
add action=drop chain=forward comment="FORWARD - Block WAN to LAN" \
    in-interface-list=WAN out-interface-list=LAN
add action=drop chain=forward comment=\
    "FORWARD - Isolate Subscribers from LAN" in-interface-list=SUBSCRIBERS \
    out-interface-list=LAN
add action=drop chain=forward comment="FORWARD - Drop everything else"
/ip firewall nat
add action=masquerade chain=srcnat comment="NAT - Internet Access" \
    out-interface-list=WAN
/ip route
add comment="WAN1 - Workplace" distance=1 dst-address=0.0.0.0/0 gateway=\
    192.168.7.1
/system clock
set time-zone-name=Africa/Nairobi
/system identity
set name=NEXAVO-CCR2004
/system routerboard settings
set enter-setup-on=delete-key
