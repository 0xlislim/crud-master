# -*- mode: ruby -*-
# vi: set ft=ruby :

require 'dotenv'
Dotenv.load('.env') if File.exist?('.env')

Vagrant.configure("2") do |config|

  config.vm.define "inventory-vm" do |inventory|
    inventory.vm.box = "ubuntu/jammy64"
    inventory.vm.hostname = "inventory-vm"
    inventory.vm.network "private_network", ip: "192.168.56.11"
    inventory.vm.provision "shell", path: "scripts/setup_inventory.sh"
  end

  config.vm.define "billing-vm" do |billing|
    billing.vm.box = "ubuntu/jammy64"
    billing.vm.hostname = "billing-vm"
    billing.vm.network "private_network", ip: "192.168.56.12"
    billing.vm.provision "shell", path: "scripts/setup_billing.sh"
  end

  config.vm.define "gateway-vm" do |gateway|
    gateway.vm.box = "ubuntu/jammy64"
    gateway.vm.hostname = "gateway-vm"
    gateway.vm.network "private_network", ip: "192.168.56.10"
    gateway.vm.provision "shell", path: "scripts/setup_gateway.sh"
  end

end

# TODO: pass .env variables into each VM's provisioning (env: {...}) once finalized.
