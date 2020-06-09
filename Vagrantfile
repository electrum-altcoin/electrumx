# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # All Vagrant configuration is done here. The most common configuration
  # options are documented and commented below. For a complete reference,
  # please see the online documentation at vagrantup.com.

  config.vm.define "electrumx.multicoin.co", autostart: true, primary: true do |t|
    t.vm.box = "geerlingguy/ubuntu2004"
    t.vm.synced_folder "./", "/home/electrumx"

    # Pre provisioning, install required tools for the ansible run
    t.vm.provision "shell", path: "./provisioning/vagrant_pre_provision.sh"

    t.vm.provision "ansible" do |ansible|
      ansible.playbook = "provisioning/playbook.yml"
      ansible.verbose = 'v'
      ansible.groups = {
        "vagrant" => ["electrumx.multicoin.co"]
      }
      ansible.extra_vars = { ansible_python_interpreter:"/usr/bin/python3", env: "dev" }

    end

    t.vm.provider "virtualbox" do |v|
      v.memory = 4096
      v.cpus = 4
      v.customize ["modifyvm", :id, "--nictype1", "virtio" ]
      v.customize ["modifyvm", :id, "--nictype2", "virtio" ]
      v.customize ["modifyvm", :id, "--natdnshostresolver1", "on"]
      v.customize ["modifyvm", :id, "--natdnsproxy1", "on"]
    end


    t.vm.network :private_network, ip: "192.168.33.90"
    t.vm.hostname = "electrumx.multicoin.co"
  end

end
