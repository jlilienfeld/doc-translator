# Overview

Scratch notes of how I got CUDA deployed on Ubuntu 24.04

References:
https://idroot.us/install-cuda-ubuntu-24-04/

## Instructions

Create a file at /etc/modprobe.d/blacklist-nouveau.conf with the following contents:

```bash
blacklist nouveau
options nouveau modeset=0
```

Regenerate the kernel initramfs:
```bash
sudo update-initramfs -u
```

That will disable some module that conflicts with CUDA.

You will need to install build-essentials:
```bash
sudo apt install build-essential
```


```bash
wget https://developer.download.nvidia.com/compute/cuda/12.5.0/local_installers/cuda_12.5.0_555.42.02_linux.run
sudo sh cuda_12.5.0_555.42.02_linux.run
```

If you get told that a driver was already in place, you can consult:
```bash
cat /var/log/cuda-installer.log
```
To see what command you may use to track and kill the conflicting modules
(I'd rather let the run have full control to ensure all the modules versions are
 compatible with each other)

That did it for me:
```bash
apt list --installed | grep -e nvidia-driver-[0-9][0-9][0-9] -e nvidia-[0-9][0-9][0-9]

# apt -purge <each package here>
```

