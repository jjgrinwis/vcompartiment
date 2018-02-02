# -*- mode: python; python-indent: 4 -*-
import ncs
from ncs.application import Service

# import some modules to caculate subnet
import socket
import struct

# ------------------------
# SERVICE CALLBACK EXAMPLE
# ------------------------
class ServiceCallbacks(Service):

    def _convert_to_wildcard(self, mask): 
      # _ private functin
      # Could use python3 ipaddress module in future
      mask_bytes = struct.unpack('BBBB', socket.inet_aton(mask))
      inverted_bytes = struct.pack('BBBB', *[~x & 0xFF for x in mask_bytes])
      return socket.inet_ntoa(inverted_bytes)

    def _build_acl_rule(self, rule):
      # turn our different leafs into a single string
      # going to use .format in stead of simple +
      # format: "permit ip 10.2.2.0 0.0.0.255 10.3.3.0 0.0.0.255 log"
      # for this poc only IP supported but this can easly be expanded with more options.
      acl_rule = "{0} ip {1} {2} {3} {4} log".format(rule.action,rule.src_ip, \
                                              self._convert_to_wildcard(rule.src_mask),rule.dest_ip, \
                                              self._convert_to_wildcard(rule.dest_mask))
      self.log.info("ACL rule created=", acl_rule)
      return acl_rule

    # The create() callback is invoked inside NCS FASTMAP and
    # must always exist.
    @Service.create
    def cb_create(self, tctx, root, service, proplist):
        self.log.info('Service create(service=', service._path, ')')

        # we can't use ncs.template.Variables to add a list of ACL rules
        # we need to the apply template for every rule
        for rule in service.access_list_rules:
          self.log.info('processing rule=', rule)

          # create template object to simplify passing of variables when applying a template.
          vars = ncs.template.Variables()
          vars.add('DEVICE', service.device)
          vars.add('ACL_NAME', service.name)
          vars.add('ACL_RULE', self._build_acl_rule(rule))
          
          # so we have our vars, now apply to template object with our variable instance
          template = ncs.template.Template(service)
          template.apply('vfirewall-template', vars)

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
        self.register_service('vfirewall-servicepoint', ServiceCallbacks)

        # If we registered any callback(s) above, the Application class
        # took care of creating a daemon (related to the service/action point).

        # When this setup method is finished, all registrations are
        # considered done and the application is 'started'.

    def teardown(self):
        # When the application is finished (which would happen if NCS went
        # down, packages were reloaded or some error occurred) this teardown
        # method will be called.

        self.log.info('Main FINISHED')
