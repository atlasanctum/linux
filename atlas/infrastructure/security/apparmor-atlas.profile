# Atlas Sanctum — AppArmor confinement profile
# Install: sudo apparmor_parser -r /etc/apparmor.d/atlas-node
# Path:    /etc/apparmor.d/atlas-node

#include <tunables/global>

/opt/atlas/.venv/bin/python {
  #include <abstractions/base>
  #include <abstractions/python>
  #include <abstractions/nameservice>

  # Atlas source tree (read-only)
  /opt/atlas/                r,
  /opt/atlas/**              r,
  /opt/atlas/.venv/**        r,
  /opt/atlas/.venv/bin/python ix,

  # Atlas data directory (read-write)
  /var/lib/atlas/            rw,
  /var/lib/atlas/**          rw,

  # Atlas log directory
  /var/log/atlas/            rw,
  /var/log/atlas/**          rw,

  # Temporary files
  /tmp/atlas-*/              rw,
  /tmp/atlas-**              rw,

  # Network access (API server + node sync)
  network inet  stream,
  network inet6 stream,
  network inet  dgram,

  # System info (read-only)
  /proc/sys/kernel/hostname  r,
  /etc/hostname              r,
  /etc/hosts                 r,

  # Deny everything else
  deny /home/**              rwx,
  deny /root/**              rwx,
  deny /etc/shadow           r,
  deny /etc/passwd           w,
}
