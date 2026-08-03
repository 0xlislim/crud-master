# -*- mode: ruby -*-
# vi: set ft=ruby :

# Load .env into ENV manually. The vagrant-dotenv plugin is incompatible with
# the Ruby version bundled in recent Vagrant (File.exists? was removed in
# Ruby 3.2), so we parse the file ourselves and pass it to the provision
# scripts via env: ENV.to_h below.
env_file = File.join(__dir__, ".env")
if File.exist?(env_file)
  File.readlines(env_file).each do |line|
    line = line.strip
    next if line.empty? || line.start_with?("#") || !line.include?("=")
    key, value = line.split("=", 2)
    ENV[key] ||= value
  end
end

Vagrant.configure("2") do |config|

  config.vm.define "inventory-vm" do |inventory|
    inventory.vm.box = "ubuntu/jammy64"
    inventory.vm.hostname = "inventory-vm"
    inventory.vm.network "private_network", ip: "192.168.56.11"
    inventory.vm.provision "shell", path: "scripts/setup_inventory.sh", env: ENV.to_h
  end

  config.vm.define "billing-vm" do |billing|
    billing.vm.box = "ubuntu/jammy64"
    billing.vm.hostname = "billing-vm"
    billing.vm.network "private_network", ip: "192.168.56.12"
    billing.vm.provision "shell", path: "scripts/setup_billing.sh", env: ENV.to_h
  end

  config.vm.define "gateway-vm" do |gateway|
    gateway.vm.box = "ubuntu/jammy64"
    gateway.vm.hostname = "gateway-vm"
    gateway.vm.network "private_network", ip: "192.168.56.10"
    gateway.vm.provision "shell", path: "scripts/setup_gateway.sh", env: ENV.to_h
  end

end