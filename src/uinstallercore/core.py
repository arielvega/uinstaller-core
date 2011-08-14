#
# This is UInstaller "The Universal Distro Installer", a project who aims to be 
# a installer for every popular linux distro and easy to adapt to a new linux based
# distro, this project is based on the Linux Mint's work "Live Installer", who was
# a startpoint for this job.
# "Use it, adapt it and enjoy it!"
# The Uremix Team.
#

import os
import subprocess
from subprocess import Popen
import time
import shutil
import gettext
import stat
import commands
import sys
from configobj import ConfigObj

__all__ = ['SystemUser', 'HostMachine', 'FSTab', 'FSTabEntry', 'UInstallerEngine']

class SystemUser:
    ''' Represents the main user, it has a username property, a realname property and a property called password'''

    def __init__(self, username=None, realname=None, password=None):
        ''' create a new SystemUser '''
        self.username = username
        self.realname = realname
        self.password = password

class HostMachine:
    ''' Used to probe information about the host '''

    def is_laptop(self):
        ''' Returns True/False as to whether the host is a laptop '''
        ret = False
        try:
            p = Popen("laptop-detect", shell=True)
            if(p.wait() == 0 ): # we want the return code
                ret = True # its a laptop
        except:
            pass # doesn't matter, laptop-detect doesnt exist on the host
        return ret

    def get_model(self):
        ''' return the model of the pc '''
        ret = None
        try:
            model = commands.getoutput("dmidecode --string system-product-name")
            ret = model.rstrip("\r\n").lstrip()
        except:
            pass # doesn't matter.
        return ret

    def get_manufacturer(self):
        ''' return the system manufacturer '''
        ret = None
        try:
            manu = commands.getoutput("dmidecode --string system-manufacturer")
            ret = manu.rstrip("\r\n ").lstrip()
        except:
            pass # doesn't matter
        return ret

class FSTab(object):
    ''' This represents the filesystem table (/etc/fstab) '''
    def __init__(self):
        ''' This creates a new filesystem table. '''
        self._mapping = dict()

    def add_mount(self, device=None, mountpoint=None, filesystem=None, options=None, format=False):
        ''' This adds a new entry to this fstab, with the device name, mountpoint, filesystem, options and if we want to format the device. '''
        if(not self._mapping.has_key(device)):
            self._mapping[device] = FSTabEntry(device, mountpoint, filesystem, options, format)

    def remove_mount(self, device):
        ''' This removes a entry in this fstb. '''
        if(self._mapping.has_key(device)):
            del self._mapping[device]

    def get_entries(self):
        ''' Return our list of entries '''
        return self._mapping.values()

    def has_device(self, device):
        ''' Returns True/False as to whether the device exists in this fstab. '''
        return self._mapping.has_key(device)

    def has_mount(self, mountpoint):
        ''' Returns True/False as to whether the mountpoint exists in this fstab. '''
        for item in self.get_entries():
            if(item.mountpoint == mountpoint):
                return True
        return False

class FSTabEntry(object):
    ''' Represents an entry in /etc/fstab '''

    def __init__(self, device, mountpoint, filesystem, options, format):
        ''' Creates a new fstab entry;
        * device refers to de devicenode that represents this entry. 
        * mountpoint refers to the directory on which the device will be mounted.
        * filesystem refers to the filesystem of the device.
        * options is the options of the device.
        * format indicates if want to format the device. '''
        self.device = device
        self.mountpoint = mountpoint
        self.filesystem = filesystem
        self.options = options
        self.format = format

class UInstallerEngine:
    ''' This is central to the UInstaller, for the correct setting for this we need two main '.conf' files:
		UInstaller.conf: Is generic, has the configurations about directories, classes and files needed for the UInstallerEngine
		install.conf: Is specific, has to define the environment (GTK, QT, ncurses, etc.), distro name, version, live user name, etc.'''

    def __init__(self):
        ''' This creates a new InstallerEngine and setups initial configurations'''
        self._conf_file = 'uinstaller.conf'
        configuration = ConfigObj(self._conf_file)
        distribution = configuration['distribution']
        install = configuration['install']
        self._distribution_name = distribution['DISTRIBUTION_NAME']
        self._distribution_version = distribution['DISTRIBUTION_VERSION']

        self._user = None
        self._live_user = install['LIVE_USER_NAME']
        self.set_install_media(media=install['LIVE_MEDIA_SOURCE'], type=install['LIVE_MEDIA_TYPE'])

        self._grub_device = None

    def set_main_user(self, user):
        ''' Set the main user to be used by the installer '''
        if(user is not None):
            self._user = user

    def get_main_user(self):
        ''' Return the main user '''
        return self._user

    def format_device(self, device, filesystem):
        ''' Format the given device to the specified filesystem '''
        if filesystem == "swap":
            cmd = "mkswap %s" % device
        else:
            cmd = "mkfs -t %s %s" % (filesystem, device)
        print "EXECUTING: '%s'" % cmd
        p = Popen(cmd, shell=True)
        p.wait() # this blocks
        return p.returncode

    def set_install_media(self, media=None, type=None):
        ''' Sets the location of our install source '''
        self._media = media
        self._media_type = type

    def set_keyboard_options(self, layout=None, model=None):
        ''' Set the required keyboard layout and model with console-setup '''
        self._keyboard_layout = layout
        self._keyboard_model = model

    def set_hostname(self, hostname):
        ''' Set the hostname on the target machine '''
        self._hostname = hostname

    def set_install_bootloader(self, device=None):
        ''' The device to install grub to '''
        self._grub_device = device

    def add_to_blacklist(self, blacklistee):
        ''' This will add a directory or file to the blacklist, so that '''
        ''' it is not copied onto the new filesystem '''
        try:
            self.blacklist.index(blacklistee)
            self.blacklist.append(blacklistee)
        except:
        # We haven't got this item yet
            pass

    def set_progress_hook(self, progresshook):
        ''' Set a callback to be called on progress updates '''
        ''' i.e. def my_callback(progress_type, message, current_progress, total) '''
        ''' Where progress_type is any off PROGRESS_START, PROGRESS_UPDATE, PROGRESS_COMPLETE, PROGRESS_ERROR '''
        self.update_progress = progresshook
        
    def set_error_hook(self, errorhook):
        ''' Set a callback to be called on errors '''
        self.error_message = errorhook

    def get_distribution_name(self):
        return self._distribution_name

    def get_distribution_version(self):
        return self._distribution_version

    def get_locale(self):
        ''' Return the locale we're setting '''
        return self._locale

    def set_locale(self, newlocale):
        ''' Set the locale '''
        self._locale = newlocale

    def set_timezone(self, newtimezone, newtimezone_code):
        ''' Set the timezone '''
        self._timezone = newtimezone
        self._timezone_code = newtimezone_code

    def set_fstab(self, newfstab):
        ''' Set the fstab '''
        self._fstab = newfstab

    def get_fstab(self):
        ''' Return the fstab thah we have defined '''
        return self._fstab

    def install(self):
        ''' Install this baby to disk '''
        # mount the media location. GENERIC
        print " --> Installation started"
        try:
            if(not os.path.exists("/target")):
                os.mkdir("/target")
            if(not os.path.exists("/source")):
                os.mkdir("/source")
            # find the squashfs..
            root = self._media
            root_type = self._media_type
            if(not os.path.exists(root)):
                print "Base filesystem does not exist! Critical error (exiting)."
                sys.exit(1) # change to report
            root_device = None
            # format partitions as appropriate
            for item in self._fstab.get_entries():
                if(item.mountpoint == "/"):
                    root_device = item                    
                if(item.format is not None and item.format):
                    # well now, we gets to nuke stuff.
                    # report it. should grab the total count of filesystems to be formatted ..
                    self.update_progress(total=4, current=1, pulse=True, message=_("Formatting %s as %s..." % (item.device, item.format)))
                    self.format_device(item.device, item.format)    
                    item.filesystem = item.format

            # mount filesystem GENERIC
            print " --> Mounting partitions"
            self.update_progress(total=4, current=2, message=_("Mounting %s on %s") % (root, "/source/"))
            print " ------ Mounting %s on %s" % (root, "/source/")
            self.do_mount(root, "/source/", root_type, options="loop")
            self.update_progress(total=4, current=3, message=_("Mounting %s on %s") % (root_device.device, "/target/"))
            print " ------ Mounting %s on %s" % (root_device.device, "/target/")
            self.do_mount(root_device.device, "/target", root_device.filesystem, None)
            for item in self._fstab.get_entries():
                if(item.mountpoint != "/" and item.mountpoint != "swap"):
                    print " ------ Mounting %s on %s" % (item.device, "/target" + item.mountpoint)
                    os.system("mkdir -p /target" + item.mountpoint)
                    self.do_mount(item.device, "/target" + item.mountpoint, item.filesystem, None)
            
            # walk root filesystem. we're too lazy though :P GENERIC
            SOURCE = "/source/"
            DEST = "/target/"
            directory_times = []
            our_total = 0
            our_current = -1
            os.chdir(SOURCE)
            # index the files
            print " --> Indexing files"
            for top,dirs,files in os.walk(SOURCE, topdown=False):
                our_total += len(dirs) + len(files)
                self.update_progress(pulse=True, message=_("Indexing files to be copied.."))
            our_total += 1 # safenessness
            print " --> Copying files"
            for top,dirs,files in os.walk(SOURCE):
                # Sanity check. Python is a bit schitzo
                dirpath = top
                if(dirpath.startswith(SOURCE)):
                    dirpath = dirpath[len(SOURCE):]
                for name in dirs + files:
                    # following is hacked/copied from Ubiquity
                    rpath = os.path.join(dirpath, name)
                    sourcepath = os.path.join(SOURCE, rpath)
                    targetpath = os.path.join(DEST, rpath)
                    st = os.lstat(sourcepath)
                    mode = stat.S_IMODE(st.st_mode)

                    # now show the world what we're doing                    
                    our_current += 1
                    self.update_progress(total=our_total, current=our_current, message=_("Copying %s" % rpath))

                    if os.path.exists(targetpath):
                        if not os.path.isdir(targetpath):
                            os.remove(targetpath)                        

                    if stat.S_ISLNK(st.st_mode):
                        if os.path.lexists(targetpath):
                            os.unlink(targetpath)
                        linkto = os.readlink(sourcepath)
                        os.symlink(linkto, targetpath)
                    elif stat.S_ISDIR(st.st_mode):
                        if not os.path.isdir(targetpath):
                            os.mkdir(targetpath, mode)
                    elif stat.S_ISCHR(st.st_mode):                        
                        os.mknod(targetpath, stat.S_IFCHR | mode, st.st_rdev)
                    elif stat.S_ISBLK(st.st_mode):
                        os.mknod(targetpath, stat.S_IFBLK | mode, st.st_rdev)
                    elif stat.S_ISFIFO(st.st_mode):
                        os.mknod(targetpath, stat.S_IFIFO | mode)
                    elif stat.S_ISSOCK(st.st_mode):
                        os.mknod(targetpath, stat.S_IFSOCK | mode)
                    elif stat.S_ISREG(st.st_mode):
                        # we don't do blacklisting yet..
                        try:
                            os.unlink(targetpath)
                        except:
                            pass
                        self.copy_file(sourcepath, targetpath)
                    os.lchown(targetpath, st.st_uid, st.st_gid)
                    if not stat.S_ISLNK(st.st_mode):
                        os.chmod(targetpath, mode)
                    if stat.S_ISDIR(st.st_mode):
                        directory_times.append((targetpath, st.st_atime, st.st_mtime))
                    # os.utime() sets timestamp of target, not link
                    elif not stat.S_ISLNK(st.st_mode):
                        os.utime(targetpath, (st.st_atime, st.st_mtime))
                # Apply timestamps to all directories now that the items within them
                # have been copied.
            print " --> Restoring meta-info"
            for dirtime in directory_times:
                (directory, atime, mtime) = dirtime
                try:
                    self.update_progress(pulse=True, message=_("Restoring meta-information on %s" % directory))
                    os.utime(directory, (atime, mtime))
                except OSError:
                    pass
                    
            # Steps:
            our_total = 10
            our_current = 0
            # chroot GENERIC
            print " --> Chrooting"
            self.update_progress(total=our_total, current=our_current, message=_("Entering new system.."))            
            os.system("mount --bind /dev/ /target/dev/")
            os.system("mount --bind /dev/shm /target/dev/shm")
            os.system("mount --bind /dev/pts /target/dev/pts")
            os.system("mount --bind /sys/ /target/sys/")
            os.system("mount --bind /proc/ /target/proc/")
            os.system("cp -f /etc/resolv.conf /target/etc/resolv.conf")
                                          
            # remove live user GENERIC
            print " --> Removing live user"
            live_user = self._live_user
            our_current += 1
            self.update_progress(total=our_total, current=our_current, message=_("Removing live configuration (user)"))
            self.run_in_chroot("deluser %s" % live_user)
            # can happen GENERIC
            if(os.path.exists("/target/home/%s" % live_user)):
                self.run_in_chroot("rm -rf /home/%s" % live_user)
            
            # remove live-initramfs (or w/e) SPECIFIC (here's using APT)
            print " --> Removing live-initramfs"
            our_current += 1
            self.update_progress(total=our_total, current=our_current, message=_("Removing live configuration (packages)"))
            self.run_in_chroot("apt-get remove --purge --yes --force-yes live-initramfs live-installer")
            
            # add new user GENERIC
            print " --> Adding new user"
            our_current += 1
            self.update_progress(total=our_total, current=our_current, message=_("Adding user to system"))
            user = self.get_main_user()
            self.run_in_chroot("useradd -s %s -c \'%s\' -G sudo -m %s" % ("/bin/bash", user.realname, user.username))
            newusers = open("/target/tmp/newusers.conf", "w")
            newusers.write("%s:%s\n" % (user.username, user.password))
            newusers.write("root:%s\n" % user.password)
            newusers.close()
            self.run_in_chroot("cat /tmp/newusers.conf | chpasswd")
            self.run_in_chroot("rm -rf /tmp/newusers.conf")
            
            # write the /etc/fstab GENERIC
            print " --> Writing fstab"
            our_current += 1
            self.update_progress(total=our_total, current=our_current, message=_("Writing filesystem mount information"))
            # make sure fstab has default /proc and /sys entries
            if(not os.path.exists("/target/etc/fstab")):
                os.system("echo \"#### Static Filesystem Table File\" > /target/etc/fstab")
            fstabber = open("/target/etc/fstab", "a")
            fstabber.write("proc\t/proc\tproc\tnodev,noexec,nosuid\t0\t0\n")
            for item in self._fstab.get_entries():
                if(item.options is None):
                    item.options = "rw,errors=remount-ro"
                if(item.filesystem == "swap"):
                    # special case..
                    fstabber.write("%s\tswap\tswap\tsw\t0\t0\n" % item.device)
                else:
                    fstabber.write("%s\t%s\t%s\t%s\t%s\t%s\n" % (item.device, item.mountpoint, item.filesystem, item.options, "0", "0"))
            fstabber.close()
            
            # write host+hostname infos GENERIC
            print " --> Writing hostname"
            our_current += 1
            self.update_progress(total=our_total, current=our_current, message=_("Setting hostname"))
            hostnamefh = open("/target/etc/hostname", "w")
            hostnamefh.write("%s\n" % self._hostname)
            hostnamefh.close()
            hostsfh = open("/target/etc/hosts", "w")
            hostsfh.write("127.0.0.1\tlocalhost\n")
            hostsfh.write("127.0.1.1\t%s\n" % self._hostname)
            hostsfh.write("# The following lines are desirable for IPv6 capable hosts\n")
            hostsfh.write("::1     localhost ip6-localhost ip6-loopback\n")
            hostsfh.write("fe00::0 ip6-localnet\n")
            hostsfh.write("ff00::0 ip6-mcastprefix\n")
            hostsfh.write("ff02::1 ip6-allnodes\n")
            hostsfh.write("ff02::2 ip6-allrouters\n")
            hostsfh.write("ff02::3 ip6-allhosts\n")
            hostsfh.close()

            # gdm overwrite (specific to Debian/live-initramfs) SPECIFIC (here's using GDM and its config files)
            print " --> Configuring GDM"
            gdmconffh = open("/target/etc/gdm3/daemon.conf", "w")
            gdmconffh.write("# GDM configuration storage\n")
            gdmconffh.write("\n[daemon]\n")
            gdmconffh.write("\n[security]\n")
            gdmconffh.write("\n[xdmcp]\n")
            gdmconffh.write("\n[greeter]\n")
            gdmconffh.write("\n[chooser]\n")
            gdmconffh.write("\n[debug]\n")
            gdmconffh.close()

            # set the locale REVISE, update-locale is general???
            print " --> Setting the locale"
            our_current += 1
            self.update_progress(total=our_total, current=our_current, message=_("Setting locale"))
            os.system("echo \"%s.UTF-8 UTF-8\" >> /target/etc/locale.gen" % self._locale)
            self.run_in_chroot("locale-gen")
            os.system("echo \"\" > /target/etc/default/locale")
            self.run_in_chroot("update-locale LANG=\"%s.UTF-8\"" % self._locale)
            self.run_in_chroot("update-locale LANG=%s.UTF-8" % self._locale)

            # set the timezone GENERAL
            print " --> Setting the timezone"
            os.system("echo \"%s\" > /target/etc/timezone" % self._timezone_code)
            os.system("cp /target/home/ariel/Documentos/live-installer_2010.12.16.1_all/usr/share/zoneinfo/%s /target/etc/localtime" % self._timezone)
            
            # localize Firefox and Thunderbird SPECIFIC (here's using APT, FIREFOX, THUNDERBIRD, APTITUDE)
            print " --> Localizing Firefox and Thunderbird"
            self.update_progress(total=our_total, current=our_current, message=_("Localizing Firefox and Thunderbird"))
            if self._locale != "en_US":
                import commands
                os.system("apt-get update")
                self.run_in_chroot("apt-get update")
                locale = self._locale.replace("_", "-")
                               
                num_res = commands.getoutput("aptitude search firefox-l10n-%s | grep firefox-l10n-%s | wc -l" % (locale, locale))
                if num_res != "0":                    
                    self.run_in_chroot("apt-get install --yes --force-yes firefox-l10n-" + locale)
                else:
                    if "_" in self._locale:
                        language_code = self._locale.split("_")[0]
                        num_res = commands.getoutput("aptitude search firefox-l10n-%s | grep firefox-l10n-%s | wc -l" % (language_code, language_code))
                        if num_res != "0":                            
                            self.run_in_chroot("apt-get install --yes --force-yes firefox-l10n-" + language_code)
               
                num_res = commands.getoutput("aptitude search thunderbird-l10n-%s | grep thunderbird-l10n-%s | wc -l" % (locale, locale))
                if num_res != "0":
                    self.run_in_chroot("apt-get install --yes --force-yes thunderbird-l10n-" + locale)
                else:
                    if "_" in self._locale:
                        language_code = self._locale.split("_")[0]
                        num_res = commands.getoutput("aptitude search thunderbird-l10n-%s | grep thunderbird-l10n-%s | wc -l" % (language_code, language_code))
                        if num_res != "0":
                            self.run_in_chroot("apt-get install --yes --force-yes thunderbird-l10n-" + language_code)                                                                                        

            # set the keyboard options.. GENERIC
            print " --> Setting the keyboard"
            our_current += 1
            self.update_progress(total=our_total, current=our_current, message=_("Setting keyboard options"))
            consolefh = open("/target/etc/default/console-setup", "r")
            newconsolefh = open("/target/etc/default/console-setup.new", "w")
            for line in consolefh:
                line = line.rstrip("\r\n")
                if(line.startswith("XKBMODEL=")):
                    newconsolefh.write("XKBMODEL=\"%s\"\n" % self._keyboard_model)
                elif(line.startswith("XKBLAYOUT=")):
                    newconsolefh.write("XKBLAYOUT=\"%s\"\n" % self._keyboard_layout)
                else:
                    newconsolefh.write("%s\n" % line)
            consolefh.close()
            newconsolefh.close()
            self.run_in_chroot("rm /etc/default/console-setup")
            self.run_in_chroot("mv /etc/default/console-setup.new /etc/default/console-setup")
            
            consolefh = open("/target/etc/default/keyboard", "r")
            newconsolefh = open("/target/etc/default/keyboard.new", "w")
            for line in consolefh:
                line = line.rstrip("\r\n")
                if(line.startswith("XKBMODEL=")):
                    newconsolefh.write("XKBMODEL=\"%s\"\n" % self._keyboard_model)
                elif(line.startswith("XKBLAYOUT=")):
                    newconsolefh.write("XKBLAYOUT=\"%s\"\n" % self._keyboard_layout)
                else:
                    newconsolefh.write("%s\n" % line)
            consolefh.close()
            newconsolefh.close()
            self.run_in_chroot("rm /etc/default/keyboard")
            self.run_in_chroot("mv /etc/default/keyboard.new /etc/default/keyboard")

            # write MBR (grub) SPECIFIC (here's using GRUB)
            print " --> Configuring Grub"
            our_current += 1
            if(self._grub_device is not None):
                self.update_progress(pulse=True, total=our_total, current=our_current, message=_("Installing bootloader"))
                print " --> Running grub-install"
                self.run_in_chroot("grub-install --force %s" % self._grub_device)
                self.configure_grub(our_total, our_current)
                grub_retries = 0
                while (not self.check_grub(our_total, our_current)):
                    self.configure_grub(our_total, our_current)
                    grub_retries = grub_retries + 1
                    if grub_retries >= 5:
                        self.error_message(critical=True, message=_("WARNING: The grub bootloader was not configured properly! You need to configure it manually."))
                        break
                        
            # write MBR (grub) SPECIFIC (here's using APT)
            print " --> Cleaning APT"
            our_current += 1
            self.update_progress(pulse=True, total=our_total, current=our_current, message=_("Cleaning APT"))
            os.system("chroot /target/ /bin/sh -c \"dpkg --configure -a\"")
            
            # now unmount it GENERIC
            print " --> Unmounting partitions"
            os.system("umount --force /target/dev/shm")
            os.system("umount --force /target/dev/pts")
            os.system("umount --force /target/dev/")
            os.system("umount --force /target/sys/")
            os.system("umount --force /target/proc/")
            os.system("rm -rf /target/etc/resolv.conf")
            for item in self._fstab.get_entries():
                if(item.mountpoint != "/" and item.mountpoint != "swap"):
                    self.do_unmount("/target" + item.mountpoint)
            self.do_unmount("/target")
            self.do_unmount("/source")

            self.update_progress(done=True, message=_("Installation finished"))
            print " --> All done"
            
        except Exception:            
            import traceback
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
    
    def run_in_chroot(self, command):
        os.system("chroot /target/ /bin/sh -c \"%s\"" % command)
        
    def configure_grub(self, our_total, our_current):
        self.update_progress(pulse=True, total=our_total, current=our_current, message=_("Configuring bootloader"))
        print " --> Running grub-mkconfig"
        self.run_in_chroot("grub-mkconfig -o /boot/grub/grub.cfg")
        grub_output = commands.getoutput("chroot /target/ /bin/sh -c \"grub-mkconfig -o /boot/grub/grub.cfg\"")
        grubfh = open("/var/log/live-installer-grub-output.log", "w")
        grubfh.writelines(grub_output)
        grubfh.close()
        
    
    def check_grub(self, our_total, our_current):
        self.update_progress(pulse=True, total=our_total, current=our_current, message=_("Checking bootloader"))
        print " --> Checking Grub configuration"
        time.sleep(5)
        found_theme = False
        found_entry = False
        if os.path.exists("/target/boot/grub/grub.cfg"):
            grubfh = open("/target/boot/grub/grub.cfg", "r")
            for line in grubfh:
                line = line.rstrip("\r\n")
                if("linuxmint.png" in line):
                    found_theme = True
                    print " --> Found Grub theme: %s " % line
                if ("menuentry" in line and "Mint" in line):
                    found_entry = True
                    print " --> Found Grub entry: %s " % line
            grubfh.close()
            return (found_entry)
        else:
            print "!No /target/boot/grub/grub.cfg file found!"
            return False

    def do_mount(self, device, dest, type, options=None):
        ''' Mount a filesystem '''
        p = None
        if(options is not None):
            cmd = "mount -o %s -t %s %s %s" % (options, type, device, dest)
        else:
            cmd = "mount -t %s %s %s" % (type, device, dest)
        print "EXECUTING: '%s'" % cmd
        p = Popen(cmd ,shell=True)
        p.wait()
        return p.returncode

    def do_unmount(self, mountpoint):
        ''' Unmount a filesystem '''
        cmd = "umount %s" % mountpoint
        print "EXECUTING: '%s'" % cmd
        p = Popen(cmd, shell=True)
        p.wait()
        return p.returncode

    def copy_file(self, source, dest):
        # TODO: Add md5 checks. BADLY needed..
        BUF_SIZE = 16 * 1024
        input = open(source, "rb")
        dst = open(dest, "wb")
        while(True):
            read = input.read(BUF_SIZE)
            if not read:
                break
            dst.write(read)
        input.close()
        dst.close()

