  file { '/usr/local/sbin/unbound_reload_forwards.py':
    ensure => present,
    owner  => root,
    group  => root,
    mode   => '0555',
    source => 'puppet:///modules/unbound/unbound_reload_forwards.py',
  }
  exec { 'unbound_reload_forwards':
    command     => '/usr/local/sbin/unbound_reload_forwards.py',
    refreshonly => true,
    require     => File['/usr/local/sbin/unbound_reload_forwards.py'],
  }
  file { '/etc/unbound/conf.d/malwarezones.conf':
    ensure => present,
    owner  => root,
    group  => unbound,
    mode   => '0640',
    source => 'puppet:///modules/unbound/malwarezones.conf',
    notify => Exec['unbound_reload_forwards'],
  }
