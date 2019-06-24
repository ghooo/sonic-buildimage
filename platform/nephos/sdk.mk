SDK_VERSION = 2.0.5
LINUX_VER = 3.16.0-9
SDK_COMMIT_ID = afea2b
NEPHOS_NPS_KERNEL = nps-modules-$(LINUX_VER)_$(SDK_VERSION)_$(SDK_COMMIT_ID)_amd64.deb
$(NEPHOS_NPS_KERNEL)_URL = "https://github.com/NephosInc/SONiC/raw/master/sdk/nps-modules-$(LINUX_VER)_$(SDK_VERSION)_$(SDK_COMMIT_ID)_amd64.deb"

SONIC_ONLINE_DEBS += $(NEPHOS_NPS_KERNEL)
