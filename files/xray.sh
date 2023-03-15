if [ "$1" = "configure" ]; then
  if ! sysctl net.ipv4.tcp_congestion_control | grep bbr > /dev/null; then
    sed -i '/net.core.default_qdisc/d' '/etc/sysctl.conf'
    sed -i '/net.ipv4.tcp_congestion_control/d' '/etc/sysctl.conf'
    echo "net.core.default_qdisc = fq" >> '/etc/sysctl.conf'
    echo "net.ipv4.tcp_congestion_control = bbr" >> '/etc/sysctl.conf'
    sysctl -p > /dev/null
  fi
fi
