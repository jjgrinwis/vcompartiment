# -*- mode: python; python-indent: 4 -*-
# import two extra package for netmask calculation
import socket
import struct

import ncs
from ncs.application import Service

# ------------------------
# SERVICE CALLBACK EXAMPLE
# ------------------------
class ServiceCallbacks(Service):

    # The create() callback is invoked inside NCS FASTMAP and
    # must always exist.
    @Service.create
    def cb_create(self, tctx, root, service, proplist):
        self.log.info('Service create(service=', service._path, ')')

        # create Variable object
        tvars = ncs.template.Variables()

        self.log.info('vars= ', service)

        # to keep XML simple, just get info from container and put in var.
        device = service.device_interfaces.device
        interface = service.device_interfaces.interface

        # lets get network leaf from our service
        # this is a network/subnet format just split to calculate.
        network = service.network
        ipstr, net_bits = network.split('/')

        # transform IP to int, add 1 and convert back to ip address
        ip2int = struct.unpack('!I', socket.inet_aton(ipstr))[0] + 1
        address = socket.inet_ntoa(struct.pack('!I', ip2int))

        # convert hostbits to netmask
        host_bits = 32 - int(net_bits)
        netmask = socket.inet_ntoa(struct.pack('!I', (1 << 32) - (1 << host_bits)))

        # now apply all our created vars to the template
        # device and interface added to keep XML simple, the rest pure leafs in XML template.
        tvars.add('IP_CIDR', netmask)
        tvars.add('IP_ADDRESS', address)
        tvars.add('DEVICE', device)
        tvars.add('INTERFACE', interface)
        tvars.add('IP_NETWORK', ipstr)

        self.log.info("vars= ", tvars)

        # now check if there is any vfirewall config
        if service.vfirewall.exists():
            self.log.info('vFirewall config exists, will create vFirewall instance')
            vftemplate = ncs.template.Template(service.vfirewall)
            vfvars = ncs.template.Variables()

            # create some vars to be used in our template
            vfirewall = "fw-" + service.name
            vfvars.add('NAME', vfirewall)
            vfvars.add('DEVICE', device)

            # we're now using template to write service parameters under ncs:/services/vfirewall
            # this will create our stacked vfirewall service
            vftemplate.apply('vcompartiment-vfirewall-template', vfvars)

            self.log.info("vars= ", vfvars)

            # name of vfirewall ACL used in this vcompartiment service
            tvars.add("ACL", vfirewall)
        else:
            tvars.add("ACL", "default-deny")

        # check if device is set, if not don't try to apply the template
        if device:
            self.log.info("configuring device ", device)
            template = ncs.template.Template(service)
            template.apply('vcompartiment-template', tvars)
            template.apply('vcompartiment-bgp-template', tvars)

    # The pre_modification() and post_modification() callbacks are optional,
    # and are invoked outside FASTMAP. pre_modification() is invoked before
    # create, update, or delete of the service, as indicated by the enum
    # ncs_service_operation op parameter. Conversely
    # post_modification() is invoked after create, update, or delete
    # of the service. These functions can be useful e.g. for
    # allocations that should be stored and existing also when the
    # service instance is removed.

    # @Service.pre_lock_create
    # def cb_pre_lock_create(self, tctx, root, service, proplist):
    #     self.log.info('Service plcreate(service=', service._path, ')')

    # @Service.pre_modification
    # def cb_pre_modification(self, tctx, op, kp, root, proplist):
    #     self.log.info('Service premod(service=', kp, ')')

    # @Service.post_modification
    # def cb_post_modification(self, tctx, op, kp, root, proplist):
    #     self.log.info('Service premod(service=', kp, ')')


# ---------------------------------------------
# COMPONENT THREAD THAT WILL BE STARTED BY NCS.
# ---------------------------------------------
class Main(ncs.application.Application):
    def setup(self):
        # The application class sets up logging for us. It is accessible
        # through 'self.log' and is a ncs.log.Log instance.
        self.log.info('Main RUNNING')

        # Service callbacks require a registration for a 'service point',
        # as specified in the corresponding data model.
        #
        self.register_service('vcompartiment-servicepoint', ServiceCallbacks)

        # If we registered any callback(s) above, the Application class
        # took care of creating a daemon (related to the service/action point).

        # When this setup method is finished, all registrations are
        # considered done and the application is 'started'.

    def teardown(self):
        # When the application is finished (which would happen if NCS went
        # down, packages were reloaded or some error occurred) this teardown
        # method will be called.

        self.log.info('Main FINISHED')
