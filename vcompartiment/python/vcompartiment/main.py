# -*- mode: python; python-indent: 4 -*-
import ncs
from ncs.application import Service

# some tools to calculate subnet
import socket
import struct


# ------------------------
# SERVICE CALLBACK EXAMPLE
# ------------------------
class ServiceCallbacks(Service):

    # The create() callback is invoked inside NCS FASTMAP and
    # must always exist.
    @Service.create
    def cb_create(self, tctx, root, service, proplist):
        self.log.info('Service create(service=', service._path, ')')

        vars = ncs.template.Variables()

        # lets get network leaf from our service
        # this is a network/subnet format
        self.log.info('vars= ',service)
        network = service.network
        device = service.device_interfaces.device
        interface = service.device_interfaces.interface
        vzone = service.vzone
        vlan_id = service.vlan_id
        self.log.info('network= ', network)

        # now split received network and calculate CIDR and GW address
        ipstr, net_bits = network.split('/')
        ip2int = struct.unpack('!I', socket.inet_aton(ipstr))[0] + 1
        address = socket.inet_ntoa(struct.pack('!I', ip2int))
        host_bits = 32 - int(net_bits)
        netmask = socket.inet_ntoa(struct.pack('!I', (1 << 32) - (1 << host_bits)))

        # now apply our vars to the template
        vars.add('IP_CIDR', netmask) 
        vars.add('IP_ADDRESS', address)
        vars.add('DEVICE', device) 
        vars.add('INTERFACE', interface)
        vars.add('VLAN-ID', vlan_id)
        vars.add('VZONE', vzone)
        vars.add('IP_NETWORK', ipstr)

        self.log.info('vars= ',vars)

        # ow check if there is any vfirewall config
        if service.vfirewall.exists():
          self.log.info('vFirewall config exists, will create vFirewall instance')
          vftemplate = ncs.template.Template(service.vfirewall) 
          tvars = ncs.template.Variables()
          vfirewall = "fw-" + service.name 
          tvars.add('NAME', vfirewall)
          tvars.add('DEVICE', device)
          vftemplate.apply('vcompartiment-vfirewall-template', tvars)
          self.log.info('vars= ', tvars)
          vars.add("ACL", vfirewall);
        else:
          vars.add("ACL", "default-deny");

        template = ncs.template.Template(service)
        template.apply('vcompartiment-template', vars)
        template.apply('vcompartiment-bgp-template', vars)


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
