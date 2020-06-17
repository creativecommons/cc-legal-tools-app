Vagrant.require_version ">= 1.8.7"

Vagrant.configure("2") do |config|
  config.vm.box = "kaorimatz/ubuntu-16.04-amd64"
  config.vm.network :private_network, ip: "33.33.33.10"
  config.vm.provider :virtualbox do |vbox|
    vbox.customize ["modifyvm", :id, "--memory", "1024"]
  end
end
