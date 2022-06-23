  mkdir -p deb/etc/ deb/usr/sbin/ deb/usr/bin/ deb/etc/systemd/system tmp/
  unzip tmp/vnstat*.zip -d tmp/
  cd tmp/vnstat-* || exit 1
  ./configure && make
  cp vnstat ../../deb/usr/bin/
  cp vnstatd ../../deb/usr/sbin/
  cp cfg/vnstat.conf ../../deb/etc/
  cp examples/systemd/vnstat.service ../../deb/etc/systemd/system/
