if [ "\$1" = "configure" ]; then
  if ! getent group caddy > /dev/null; then
    groupadd --system caddy
  fi
  if ! getent passwd caddy > /dev/null; then
    useradd --system \
      --gid caddy \
      --create-home \
      --home-dir /var/lib/caddy \
      --shell /usr/sbin/nologin \
      --comment "Caddy web server" \
      caddy
  fi
  if getent group www-data > /dev/null; then
    usermod -aG www-data caddy
  fi
  if [ ! -d /var/log/caddy ]; then
    mkdir -p /var/log/caddy
    chown -R caddy:caddy /var/log/caddy
  fi
  if ! sysctl net.ipv4.tcp_congestion_control | grep bbr > /dev/null; then
    sed -i '/net.core.default_qdisc/d' '/etc/sysctl.conf'
    sed -i '/net.ipv4.tcp_congestion_control/d' '/etc/sysctl.conf'
    echo "net.core.default_qdisc = fq" >> '/etc/sysctl.conf'
    echo "net.ipv4.tcp_congestion_control = bbr" >> '/etc/sysctl.conf'
    sysctl -p > /dev/null
  fi
fi
