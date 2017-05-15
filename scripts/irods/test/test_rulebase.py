from __future__ import print_function
import sys
if sys.version_info >= (2, 7):
    import unittest
else:
    import unittest2 as unittest
import os
import socket
import tempfile
import time  # remove once file hash fix is commited #2279
import copy
import inspect
import json

from .. import lib
from .. import test
from . import settings
from .resource_suite import ResourceBase
from ..configuration import IrodsConfig
from ..controller import IrodsController
from .rule_texts_for_tests import rule_texts, rule_files


class Test_Rulebase(ResourceBase, unittest.TestCase):
    plugin_name = IrodsConfig().default_rule_engine_plugin
    class_name = 'Test_Rulebase'

    def setUp(self):
        super(Test_Rulebase, self).setUp()

    def tearDown(self):
        super(Test_Rulebase, self).tearDown()

    def test_client_server_negotiation__2564(self):
        corefile = IrodsConfig().core_re_directory + "/" + rule_files[self.plugin_name]
        with lib.file_backed_up(corefile):
            client_update = {
                'irods_client_server_policy': 'CS_NEG_REFUSE'
            }

            session_env_backup = copy.deepcopy(self.admin.environment_file_contents)
            self.admin.environment_file_contents.update(client_update)

            time.sleep(2)  # remove once file hash fix is commited #2279
            rule_string = rule_texts[self.plugin_name][self.class_name]['test_client_server_negotiation__2564']
            lib.prepend_string_to_file(rule_string, corefile)
            time.sleep(2)  # remove once file hash fix is commited #2279

            self.admin.assert_icommand( 'ils','STDERR_SINGLELINE','CLIENT_NEGOTIATION_ERROR')

            self.admin.environment_file_contents = session_env_backup

    def test_msiDataObjWrite__2795(self):
        rule_file = "test_rule_file.r"
        rule_string = rule_texts[self.plugin_name][self.class_name]['test_msiDataObjWrite__2795_1'] + self.admin.session_collection + rule_texts[self.plugin_name][self.class_name]['test_msiDataObjWrite__2795_2']
        with open(rule_file, 'wt') as f:
            print(rule_string, file=f, end='')

        test_file = self.admin.session_collection+'/test_file.txt'

        self.admin.assert_icommand('irule -F ' + rule_file)
        self.admin.assert_icommand('ils -l','STDOUT_SINGLELINE','test_file')
        self.admin.assert_icommand('iget -f '+test_file)

        with open("test_file.txt", 'r') as f:
            file_contents = f.read()

        assert( not file_contents.endswith('\0') )

    @unittest.skipIf(plugin_name == 'irods_rule_engine_plugin-python', 'Skip for Python REP')
    def test_irods_re_infinite_recursion_3169(self):
        rules_to_prepend = rule_texts[self.plugin_name][self.class_name]['test_irods_re_infinite_recursion_3169']
        corefile = IrodsConfig().core_re_directory + "/" + rule_files[self.plugin_name]
        with lib.file_backed_up(corefile):
            time.sleep(2) # remove once file hash fix is commited #2279
            lib.prepend_string_to_file(rules_to_prepend, corefile)
            time.sleep(2) # remove once file hash fix is commited #2279

            test_file = 'rulebasetestfile'
            lib.touch(test_file)
            self.admin.assert_icommand(['iput', test_file])

    def test_acPostProcForPut_replicate_to_multiple_resources(self):
        # create new resources
        hostname = socket.gethostname()
        self.admin.assert_icommand("iadmin mkresc r1 unixfilesystem " + hostname + ":/tmp/irods/r1", 'STDOUT_SINGLELINE', "Creating")
        self.admin.assert_icommand("iadmin mkresc r2 unixfilesystem " + hostname + ":/tmp/irods/r2", 'STDOUT_SINGLELINE', "Creating")

        corefile = IrodsConfig().core_re_directory + "/" + rule_files[self.plugin_name]
        with lib.file_backed_up(corefile):
            time.sleep(2)  # remove once file hash fix is commited #2279
#            lib.prepend_string_to_file('\nacPostProcForPut { replicateMultiple( \"r1,r2\" ); }\n', corefile)
            lib.prepend_string_to_file(rule_texts[self.plugin_name][self.class_name]['test_acPostProcForPut_replicate_to_multiple_resources_1'], corefile)
            time.sleep(2)  # remove once file hash fix is commited #2279

            # add new rule to end of core.re
            newrule = rule_texts[self.plugin_name][self.class_name]['test_acPostProcForPut_replicate_to_multiple_resources_2']

            time.sleep(2)  # remove once file hash fix is commited #2279
            lib.prepend_string_to_file(newrule, corefile)
            time.sleep(2)  # remove once file hash fix is commited #2279

            # put data
            tfile = "rulebasetestfile"
            lib.touch(tfile)
            self.admin.assert_icommand(['iput', tfile])

            # check replicas
            self.admin.assert_icommand(['ils', '-L', tfile], 'STDOUT_MULTILINE', [' demoResc ', ' r1 ', ' r2 '])

            # clean up and remove new resources
            self.admin.assert_icommand("irm -rf " + tfile)
            self.admin.assert_icommand("iadmin rmresc r1")
            self.admin.assert_icommand("iadmin rmresc r2")

        time.sleep(2)  # remove once file hash fix is commited #2279

    def test_dynamic_pep_with_rscomm_usage(self):
        # save original core.re
        corefile = os.path.join(IrodsConfig().core_re_directory, rule_files[self.plugin_name])
        origcorefile = os.path.join(IrodsConfig().core_re_directory, "core.re.orig")
        os.system("cp " + corefile + " " + origcorefile)

        # add dynamic PEP with rscomm usage
        time.sleep(1)  # remove once file hash fix is commited #2279
        newrule = rule_texts[self.plugin_name][self.class_name]['test_dynamic_pep_with_rscomm_usage']
        lib.prepend_string_to_file(newrule, corefile);
        time.sleep(1)  # remove once file hash fix is commited #2279

        # check rei functioning
        self.admin.assert_icommand("iget " + self.testfile + " - ", 'STDOUT_SINGLELINE', self.testfile)

        # restore core.re
        time.sleep(1)  # remove once file hash fix is commited #2279
        os.system("cp " + origcorefile + " " + corefile)
        time.sleep(1)  # remove once file hash fix is commited #2279

    @unittest.skipIf(test.settings.TOPOLOGY_FROM_RESOURCE_SERVER, 'Skip for topology testing from resource server: reads re server log')
    @unittest.skipUnless(plugin_name == 'irods_rule_engine_plugin-irods_rule_language', 'tests cache update - only applicable for irods_rule_language REP')
    def test_rulebase_update__2585(self):
        irods_config = IrodsConfig()
        my_rule = rule_texts[self.plugin_name][self.class_name]['test_rulebase_update__2585_1']
        rule_file = 'my_rule.r'
        with open(rule_file, 'wt') as f:
            print(my_rule, file=f, end='')

        server_config_filename = irods_config.server_config_path

        # load server_config.json to inject a new rule base
        with open(server_config_filename) as f:
            svr_cfg = json.load(f)

        # inject a new rule base into the native rule engine
        svr_cfg['plugin_configuration']['rule_engines'][0]['plugin_specific_configuration']['re_rulebase_set'] = ["test", "core"]

        # dump to a string to repave the existing server_config.json
        new_server_config=json.dumps(svr_cfg, sort_keys=True,indent=4, separators=(',', ': '))

        with lib.file_backed_up(irods_config.server_config_path):
            test_re = os.path.join(irods_config.core_re_directory, 'test.re')
            # write new rule file to config dir
            with open(test_re, 'wt') as f:
                print(rule_texts[self.plugin_name][self.class_name]['test_rulebase_update__2585_2'], file=f, end='')

            # repave the existing server_config.json
            with open(server_config_filename, 'w') as f:
                f.write(new_server_config)

            IrodsController().restart()
            # checkpoint log to know where to look for the string
            initial_log_size = lib.get_file_size_by_path(irods_config.server_log_path)
            self.admin.assert_icommand('irule -F ' + rule_file)
            time.sleep(35)  # wait for test to fire
            assert lib.count_occurrences_of_string_in_log(irods_config.server_log_path, 'TEST_STRING_TO_FIND_1_2585', start_index=initial_log_size)

            # repave rule with new string
            os.unlink(test_re)
            with open(test_re, 'wt') as f:
                print(rule_texts[self.plugin_name][self.class_name]['test_rulebase_update__2585_3'], file=f, end='')

            # checkpoint log to know where to look for the string
            initial_log_size = lib.get_file_size_by_path(irods_config.server_log_path)
            self.admin.assert_icommand('irule -F ' + rule_file)
            time.sleep(35)  # wait for test to fire
            assert lib.count_occurrences_of_string_in_log(irods_config.server_log_path, 'TEST_STRING_TO_FIND_2_2585', start_index=initial_log_size)

        # cleanup
        IrodsController().restart()
        os.unlink(test_re)
        os.unlink(rule_file)

    @unittest.skipUnless(plugin_name == 'irods_rule_engine_plugin-irods_rule_language', 'tests cache update - only applicable for irods_rule_language REP')
    def test_rulebase_update_without_delay(self):
        irods_config = IrodsConfig()
        my_rule = rule_texts[self.plugin_name][self.class_name]['test_rulebase_update_without_delay_1']
        rule_file = 'my_rule.r'
        with open(rule_file, 'wt') as f:
            print(my_rule, file=f, end='')

        server_config_filename = irods_config.server_config_path

        # load server_config.json to inject a new rule base
        with open(server_config_filename) as f:
            svr_cfg = json.load(f)

        # inject a new rule base into the native rule engine
        svr_cfg['plugin_configuration']['rule_engines'][0]['plugin_specific_configuration']['re_rulebase_set'] = ["test", "core"]

        # dump to a string to repave the existing server_config.json
        new_server_config=json.dumps(svr_cfg, sort_keys=True,indent=4, separators=(',', ': '))

        with lib.file_backed_up(irods_config.server_config_path):
            test_re = os.path.join(irods_config.core_re_directory, 'test.re')
            # write new rule file to config dir
            with open(test_re, 'wt') as f:
                print(rule_texts[self.plugin_name][self.class_name]['test_rulebase_update_without_delay_2'], file=f, end='')

            # repave the existing server_config.json
            with open(server_config_filename, 'w') as f:
                f.write(new_server_config)

            # checkpoint log to know where to look for the string
            initial_log_size = lib.get_file_size_by_path(irods_config.server_log_path)
            self.admin.assert_icommand('irule -F ' + rule_file)
            assert lib.count_occurrences_of_string_in_log(irods_config.server_log_path, 'TEST_STRING_TO_FIND_1_NODELAY', start_index=initial_log_size)

            time.sleep(5) # ensure modify time is sufficiently different

            # repave rule with new string
            os.unlink(test_re)
            with open(test_re, 'wt') as f:
                print(rule_texts[self.plugin_name][self.class_name]['test_rulebase_update_without_delay_3'], file=f, end='')

            # checkpoint log to know where to look for the string
            initial_log_size = lib.get_file_size_by_path(irods_config.server_log_path)
            self.admin.assert_icommand('irule -F ' + rule_file)
            #time.sleep(35)  # wait for test to fire
            assert lib.count_occurrences_of_string_in_log(irods_config.server_log_path, 'TEST_STRING_TO_FIND_2_NODELAY', start_index=initial_log_size)

        # cleanup
        os.unlink(test_re)
        os.unlink(rule_file)

    @unittest.skipIf(plugin_name == 'irods_rule_engine_plugin-python', 'Python REP does not guarantee argument preservation')
    def test_argument_preservation__3236(self):
        with tempfile.NamedTemporaryFile(suffix='.r') as f:

            rule_string = rule_texts[self.plugin_name][self.class_name]['test_argument_preservation__3236']
            f.write(rule_string)
            f.flush()

            self.admin.assert_icommand('irule -F ' + f.name, 'STDOUT_SINGLELINE', 'AFTER arg1=abc arg2=def arg3=ghi')



@unittest.skipIf(test.settings.TOPOLOGY_FROM_RESOURCE_SERVER, 'Skip for topology testing from resource server: reads rods server log')
class Test_Resource_Session_Vars__3024(ResourceBase, unittest.TestCase):
    plugin_name = IrodsConfig().default_rule_engine_plugin
    class_name = 'Test_Resource_Session_Vars__3024'

    def setUp(self):
        super(Test_Resource_Session_Vars__3024, self).setUp()

        # get PEP name
        self.pep_name = self._testMethodName.split('_')[1]

        # make large test file
        self.large_file = '/tmp/largefile'
        lib.make_file(self.large_file, '64M')

    def tearDown(self):
        del self.pep_name

        # remove large test file
        os.unlink(self.large_file)

        super(Test_Resource_Session_Vars__3024, self).tearDown()

    def test_acPostProcForPut(self):
        self.pep_test_helper(commands=['iput -f {testfile}'])

    def test_acSetNumThreads(self):
        rule_body = rule_texts[self.plugin_name][self.class_name]['test_acSetNumThreads']
        self.pep_test_helper(commands=['iput -f {large_file}'], rule_body=rule_body)

    def test_acDataDeletePolicy(self):
        self.pep_test_helper(precommands=['iput -f {testfile}'], commands=['irm -f {testfile}'])

    def test_acPostProcForDelete(self):
        self.pep_test_helper(precommands=['iput -f {testfile}'], commands=['irm -f {testfile}'])

    def test_acSetChkFilePathPerm(self):
        # regular user will try to register a system file
        # e.g: /var/lib/irods/VERSION.json
        irods_config = IrodsConfig()
        path_to_register = irods_config.version_path
        commands = [('ireg {path_to_register} {{target_obj}}'.format(**locals()), 'STDERR_SINGLELINE', 'PATH_REG_NOT_ALLOWED')]
        self.pep_test_helper(commands=commands, target_name=os.path.basename(path_to_register))

    def test_acPostProcForFilePathReg(self):
        # admin user will register a file
        sess=self.admin

        # make new physical file in user's vault
        reg_file_path = os.path.join(sess.get_vault_session_path(), 'reg_test_file')
        lib.make_dir_p(os.path.dirname(reg_file_path))
        lib.touch(reg_file_path)

        commands = ['ireg {reg_file_path} {{target_obj}}'.format(**locals())]
        self.pep_test_helper(commands=commands, target_name=os.path.basename(reg_file_path), user_session=sess)

    def test_acPostProcForCopy(self):
        self.pep_test_helper(precommands=['iput -f {testfile}'], commands=['icp {testfile} {testfile}_copy'])

    def test_acSetVaultPathPolicy(self):
        self.pep_test_helper(commands=['iput -f {testfile}'])

    def test_acPreprocForDataObjOpen(self):
        client_rule = rule_texts[self.plugin_name][self.class_name]['test_acPreprocForDataObjOpen']

        self.pep_test_helper(precommands=['iput -f {testfile}'], commands=['irule -F {client_rule_file}'], client_rule=client_rule)

    def test_acPostProcForOpen(self):
        # prepare rule file
        client_rule = rule_texts[self.plugin_name][self.class_name]['test_acPostProcForOpen']

        self.pep_test_helper(precommands=['iput -f {testfile}'], commands=['irule -F {client_rule_file}'], client_rule=client_rule)

    def get_resource_property_list(self, session):
        # query for resource properties
        columns = ('RESC_ZONE_NAME, '
                   'RESC_FREE_SPACE, '
                   'RESC_STATUS, '
                   'RESC_ID, '
                   'RESC_NAME, '
                   'RESC_TYPE_NAME, '
                   'RESC_LOC, '
                   'RESC_CLASS_NAME, '
                   'RESC_VAULT_PATH, '
                   'RESC_INFO, '
                   'RESC_COMMENT, '
                   'RESC_CREATE_TIME, '
                   'RESC_MODIFY_TIME')
        resource = session.default_resource
        query = '''iquest "SELECT {columns} WHERE RESC_NAME ='{resource}'"'''.format(**locals())
        result = session.run_icommand(query)[0]

        # last line is iquest default formatting separator
        resource_property_list = result.splitlines()[:-1]

        # make sure property list is not empty
        self.assertTrue(len(resource_property_list))

        return resource_property_list

    def make_pep_rule(self, pep_name, rule_body):
        # prepare rule
        # rule will write PEP name as well as
        # resource related rule session vars to server log
        write_statements = 'writeLine("serverLog", "{pep_name}");'.format(**locals())
        write_statements += ('writeLine("serverLog", $KVPairs.zoneName);'
                      'writeLine("serverLog", $KVPairs.freeSpace);'
                      'writeLine("serverLog", $KVPairs.quotaLimit);'
                      'writeLine("serverLog", $KVPairs.rescStatus);'
                      'writeLine("serverLog", $KVPairs.rescId);'
                      'writeLine("serverLog", $KVPairs.rescName);'
                      'writeLine("serverLog", $KVPairs.rescType);'
                      'writeLine("serverLog", $KVPairs.rescLoc);'
                      'writeLine("serverLog", $KVPairs.rescClass);'
                      'writeLine("serverLog", $KVPairs.rescVaultPath);'
                      'writeLine("serverLog", $KVPairs.rescInfo);'
                      'writeLine("serverLog", $KVPairs.rescComments);'
                      'writeLine("serverLog", $KVPairs.rescCreate);'
                      'writeLine("serverLog", $KVPairs.rescModify)')

        return '{pep_name} {{ {write_statements};{rule_body} }}'.format(**locals())

    def make_pep_rule_python(self, pep_name, rule_body):
        # prepare rule
        # rule will write PEP name as well as
        # resource related rule session vars to server log
        write_statements = '    callback.writeLine("serverLog", "{pep_name}")\n'.format(**locals())
        write_statements += ('    callback.writeLine("serverLog", session_vars["KVPairs"]["zoneName"])\n'
                      '    callback.writeLine("serverLog", session_vars["KVPairs"]["freeSpace"])\n'
                      '    callback.writeLine("serverLog", session_vars["KVPairs"]["quotaLimit"])\n'
                      '    callback.writeLine("serverLog", session_vars["KVPairs"]["rescStatus"])\n'
                      '    callback.writeLine("serverLog", session_vars["KVPairs"]["rescId"])\n'
                      '    callback.writeLine("serverLog", session_vars["KVPairs"]["rescName"])\n'
                      '    callback.writeLine("serverLog", session_vars["KVPairs"]["rescType"])\n'
                      '    callback.writeLine("serverLog", session_vars["KVPairs"]["rescLoc"])\n'
                      '    callback.writeLine("serverLog", session_vars["KVPairs"]["rescClass"])\n'
                      '    callback.writeLine("serverLog", session_vars["KVPairs"]["rescVaultPath"])\n'
                      '    callback.writeLine("serverLog", session_vars["KVPairs"]["rescInfo"])\n'
                      '    callback.writeLine("serverLog", session_vars["KVPairs"]["rescComments"])\n'
                      '    callback.writeLine("serverLog", session_vars["KVPairs"]["rescCreate"])\n'
                      '    callback.writeLine("serverLog", session_vars["KVPairs"]["rescModify"])\n')

        return 'def {pep_name}(rule_args, callback):\n{write_statements}\n{rule_body}'.format(**locals())

#    def make_new_server_config_json(self, server_config_filename):
#        # load server_config.json to inject a new rule base
#        with open(server_config_filename) as f:
#            svr_cfg = json.load(f)
#
#        # inject a new rule base into the native rule engine
#        svr_cfg['plugin_configuration']['rule_engines'][0]['plugin_specific_configuration']['re_rulebase_set'] = ["test", "core"]
#
#        # dump to a string to repave the existing server_config.json
#        return json.dumps(svr_cfg, sort_keys=True,indent=4, separators=(',', ': '))

    def pep_test_helper(self, precommands=[], commands=[], rule_body='', client_rule=None, target_name=None, user_session=None):
        irods_config = IrodsConfig()
#        test_re = os.path.join(irods_config.core_re_directory, 'test.re')
#        server_config_filename = irods_config.server_config_path
        core_re = os.path.join(irods_config.core_re_directory, rule_files[self.plugin_name])
        pep_name = self.pep_name

        # user session
        if user_session is None:
            if client_rule is None:
                user_session = self.user0
            else:
                # Python rule engine needs admin privileges to run irule
                user_session = self.admin

        # local vars to format command strings
        testfile = self.testfile
        large_file = self.large_file
        if target_name is None:
            target_name = testfile
        target_obj = '/'.join([user_session.session_collection, target_name])

        # query for resource properties
        resource_property_list = self.get_resource_property_list(user_session)

#        # make new server configuration with additional re file
#        new_server_config = self.make_new_server_config_json(server_config_filename)

#        with lib.file_backed_up(server_config_filename):
        with lib.file_backed_up(core_re):
            # make pep rule
            if self.plugin_name == 'irods_rule_engine_plugin-irods_rule_language':
                test_rule = self.make_pep_rule(pep_name, rule_body)
            elif self.plugin_name == 'irods_rule_engine_plugin-python':
                test_rule = self.make_pep_rule_python(pep_name, rule_body)

            # write pep rule into test_re
#            with open(test_re, 'w') as f:
#                f.write(test_rule)
            time.sleep(2)
            lib.prepend_string_to_file(test_rule, core_re)
            time.sleep(2)

#            # repave the existing server_config.json to add test_re
#            with open(server_config_filename, 'w') as f:
#                f.write(new_server_config)

            # make client-side rule file
            if client_rule is not None:
                client_rule_file = "test_rule_file.r"
                with open(client_rule_file, 'w') as f:
                    f.write(client_rule.format(**locals()))

            # perform precommands
            for c in precommands:
                if isinstance(c, tuple):
                    user_session.assert_icommand(c[0].format(**locals()), c[1], c[2])
                else:
                    user_session.assert_icommand(c.format(**locals()))

            # checkpoint log to know where to look for the string
            initial_log_size = lib.get_file_size_by_path(irods_config.server_log_path)

            # perform commands to hit PEP
            for c in commands:
                if isinstance(c, tuple):
                    user_session.assert_icommand(c[0].format(**locals()), c[1], c[2])
                else:
                    user_session.assert_icommand(c.format(**locals()))

            # delete client-side rule file
            if client_rule is not None:
                os.unlink(client_rule_file)

            # confirm that PEP was hit by looking for pep name in server log
            assert lib.count_occurrences_of_string_in_log(irods_config.server_log_path, pep_name, start_index=initial_log_size)

            # check that resource session vars were written to the server log
            for line in resource_property_list:
                column = line.rsplit('=', 1)[0].strip()
                property = line.rsplit('=', 1)[1].strip()
                if property:
                    if column != 'RESC_MODIFY_TIME':
                        assert lib.count_occurrences_of_string_in_log(irods_config.server_log_path, property, start_index=initial_log_size)

        # cleanup
        user_session.run_icommand('irm -f {target_obj}'.format(**locals()))
#        os.unlink(test_re)

    @unittest.skipIf(plugin_name == 'irods_rule_engine_plugin-python', 'Skip for Python REP')
    def test_genquery_foreach_MAX_SQL_ROWS_multiple__3489(self):
        MAX_SQL_ROWS = 256 # needs to be the same as constant in server code
        filename = 'test_genquery_foreach_MAX_SQL_ROWS_multiple__3489_dummy_file'
        lib.make_file(filename, 1)
        data_object_prefix = 'loiuaxnlaskdfpiewrnsliuserd'
        for i in range(MAX_SQL_ROWS):
            self.admin.assert_icommand(['iput', filename, '{0}_file_{1}'.format(data_object_prefix, i)])

        rule_file = 'test_genquery_foreach_MAX_SQL_ROWS_multiple__3489.r'
        rule_string = '''
test_genquery_foreach_MAX_SQL_ROWS_multiple__3489 {{
    foreach(*rows in select DATA_ID where DATA_NAME like '{0}%') {{
        *id = *rows.DATA_ID;
        writeLine("serverLog", "GGGGGGGGGGGGGGG *id");
    }}
}}
INPUT null
OUTPUT ruleExecOut
'''.format(data_object_prefix)

        with open(rule_file, 'w') as f:
            f.write(rule_string)

        self.admin.assert_icommand(['irule', '-F', rule_file])
        os.unlink(rule_file)