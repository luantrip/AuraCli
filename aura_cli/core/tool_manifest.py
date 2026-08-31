"""Generated tool metadata. Run scripts/generate_tool_manifest.py to update."""

from typing import Any, Final

TOOL_MANIFEST: Final[list[dict[str, Any]]] = [{'name': 'advanced_grep_search',
  'category': 'development',
  'description': 'Codebase: advanced_grep_search',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.codebase_tools',
  'qualname': 'advanced_grep_search',
  'schema': {'type': 'function',
             'function': {'name': 'advanced_grep_search',
                          'description': 'Searches file contents using a regex pattern with '
                                         'context lines, extension filters, and more.',
                          'parameters': {'type': 'object',
                                         'properties': {'pattern': {'type': 'string',
                                                                    'description': 'Regex pattern '
                                                                                   'to search '
                                                                                   'for.'},
                                                        'path': {'type': 'string',
                                                                 'description': 'Root directory to '
                                                                                'search (default: '
                                                                                'current dir).'},
                                                        'options': {'type': 'string',
                                                                    'description': 'Dict with '
                                                                                   'optional '
                                                                                   'keys:'}},
                                         'required': ['pattern']}}}},
 {'name': 'analyze_code',
  'category': 'development',
  'description': 'Dev: analyze_code',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.dev_tools',
  'qualname': 'analyze_code',
  'schema': {'type': 'function',
             'function': {'name': 'analyze_code',
                          'description': 'Analyse code structure and return metrics.',
                          'parameters': {'type': 'object',
                                         'properties': {'file_path': {'type': 'string',
                                                                      'description': 'Parâmetro '
                                                                                     'file_path'}},
                                         'required': ['file_path']}}}},
 {'name': 'analyze_code_nlp',
  'category': 'development',
  'description': 'Dev: analyze_code_nlp',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.tools.dev_tools',
  'qualname': 'analyze_code_nlp',
  'schema': {'type': 'function',
             'function': {'name': 'analyze_code_nlp',
                          'description': 'Analyse code using NLP and return insights.',
                          'parameters': {'type': 'object',
                                         'properties': {'file_path': {'type': 'string',
                                                                      'description': 'Parâmetro '
                                                                                     'file_path'}},
                                         'required': ['file_path']}}}},
 {'name': 'analyze_dependencies',
  'category': 'analysis',
  'description': 'Nexus: Dependency Graph',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.nim_integration',
  'qualname': 'analyze_dependencies',
  'schema': {'type': 'function',
             'function': {'name': 'analyze_dependencies',
                          'description': 'Analyzes codebase dependencies to build an import graph '
                                         'using Aura Nexus.',
                          'parameters': {'type': 'object',
                                         'properties': {'path': {'type': 'string',
                                                                 'description': 'Root path to '
                                                                                'analyze'}},
                                         'required': []}}}},
 {'name': 'analyze_project_documentation',
  'category': 'development',
  'description': 'Codebase: analyze_project_documentation',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.project_insights',
  'qualname': 'analyze_project_documentation',
  'schema': {'type': 'function',
             'function': {'name': 'analyze_project_documentation',
                          'description': 'Evaluate documentation completeness and quality.',
                          'parameters': {'type': 'object',
                                         'properties': {'project_path': {'type': 'string',
                                                                         'description': 'Project '
                                                                                        'root '
                                                                                        '(default '
                                                                                        '".").'},
                                                        'check_completeness': {'type': 'boolean',
                                                                               'description': 'Verify '
                                                                                              'coverage '
                                                                                              'of '
                                                                                              'expected '
                                                                                              'docs '
                                                                                              '(default '
                                                                                              'True).'},
                                                        'check_quality': {'type': 'boolean',
                                                                          'description': 'Run '
                                                                                         'basic '
                                                                                         'quality '
                                                                                         'checks '
                                                                                         '(default '
                                                                                         'True).'}},
                                         'required': []}}}},
 {'name': 'analyze_project_quality',
  'category': 'development',
  'description': 'Codebase: analyze_project_quality',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.project_insights',
  'qualname': 'analyze_project_quality',
  'schema': {'type': 'function',
             'function': {'name': 'analyze_project_quality',
                          'description': 'Deep code quality analysis: duplication, cyclomatic '
                                         'complexity, code smells.',
                          'parameters': {'type': 'object',
                                         'properties': {'project_path': {'type': 'string',
                                                                         'description': 'Project '
                                                                                        'root '
                                                                                        '(default '
                                                                                        '".").'},
                                                        'focus_areas': {'type': 'string',
                                                                        'description': 'List of '
                                                                                       'analysis '
                                                                                       'areas. '
                                                                                       'Default: '
                                                                                       '["duplication", '
                                                                                       '"complexity", '
                                                                                       '"smells"].'},
                                                        'max_files': {'type': 'integer',
                                                                      'description': 'Max files to '
                                                                                     'analyse '
                                                                                     '(default '
                                                                                     '100).'}},
                                         'required': []}}}},
 {'name': 'analyze_project_security',
  'category': 'development',
  'description': 'Codebase: analyze_project_security',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.project_insights',
  'qualname': 'analyze_project_security',
  'schema': {'type': 'function',
             'function': {'name': 'analyze_project_security',
                          'description': 'Preventive security analysis of the project.',
                          'parameters': {'type': 'object',
                                         'properties': {'project_path': {'type': 'string',
                                                                         'description': 'Project '
                                                                                        'root '
                                                                                        '(default '
                                                                                        '".").'},
                                                        'check_patterns': {'type': 'boolean',
                                                                           'description': 'Search '
                                                                                          'for '
                                                                                          'insecure '
                                                                                          'patterns '
                                                                                          'in '
                                                                                          'source '
                                                                                          '(default '
                                                                                          'True).'},
                                                        'check_dependencies': {'type': 'boolean',
                                                                               'description': 'Check '
                                                                                              'known-vulnerable '
                                                                                              'dependencies '
                                                                                              '(default '
                                                                                              'True).'}},
                                         'required': []}}}},
 {'name': 'analyze_project_structure',
  'category': 'development',
  'description': 'Codebase: analyze_project_structure',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.project_analyzer',
  'qualname': 'analyze_project_structure',
  'schema': {'type': 'function',
             'function': {'name': 'analyze_project_structure',
                          'description': 'Structured full-project analysis: directories, key '
                                         'files, fronts, tech stack.',
                          'parameters': {'type': 'object',
                                         'properties': {'project_path': {'type': 'string',
                                                                         'description': 'Parâmetro '
                                                                                        'project_path'},
                                                        'include_subprojects': {'type': 'boolean',
                                                                                'description': 'Parâmetro '
                                                                                               'include_subprojects'},
                                                        'read_key_files': {'type': 'boolean',
                                                                           'description': 'Parâmetro '
                                                                                          'read_key_files'},
                                                        'max_depth': {'type': 'integer',
                                                                      'description': 'Parâmetro '
                                                                                     'max_depth'},
                                                        'analyze_architecture': {'type': 'boolean',
                                                                                 'description': 'Parâmetro '
                                                                                                'analyze_architecture'},
                                                        'analyze_dependencies': {'type': 'boolean',
                                                                                 'description': 'Parâmetro '
                                                                                                'analyze_dependencies'},
                                                        'analyze_tests': {'type': 'boolean',
                                                                          'description': 'Parâmetro '
                                                                                         'analyze_tests'}},
                                         'required': []}}}},
 {'name': 'backup_file',
  'category': 'development',
  'description': 'Dev: backup_file',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.tools.dev_tools',
  'qualname': 'backup_file',
  'schema': {'type': 'function',
             'function': {'name': 'backup_file',
                          'description': 'Create a backup copy of a file.',
                          'parameters': {'type': 'object',
                                         'properties': {'path': {'type': 'string',
                                                                 'description': 'Parâmetro path'}},
                                         'required': ['path']}}}},
 {'name': 'browse_content',
  'category': 'web',
  'description': 'Monitor: Headless Browser',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.tools.nim_integration',
  'qualname': 'browse_content',
  'schema': {'type': 'function',
             'function': {'name': 'browse_content',
                          'description': 'Fetches and renders content from a URL or local file '
                                         'using the Aura Monitor.',
                          'parameters': {'type': 'object',
                                         'properties': {'url': {'type': 'string',
                                                                'description': 'URL (http/https) '
                                                                               'or local file '
                                                                               'path'},
                                                        'mode': {'type': 'string',
                                                                 'description': 'Output format - '
                                                                                "'text' (rendered "
                                                                                "view) or 'json' "
                                                                                '(structured data '
                                                                                'with links)'}},
                                         'required': ['url']}}}},
 {'name': 'check_file_changes',
  'category': 'monitoring',
  'description': 'Sentinel: Change Detector',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.nim_integration',
  'qualname': 'check_file_changes',
  'schema': {'type': 'function',
             'function': {'name': 'check_file_changes',
                          'description': 'Detects modified, added, or deleted files since the last '
                                         'check using Aura Sentinel.',
                          'parameters': {'type': 'object',
                                         'properties': {'path': {'type': 'string',
                                                                 'description': 'Root path to '
                                                                                'monitor'}},
                                         'required': []}}}},
 {'name': 'check_port',
  'category': 'monitoring',
  'description': 'Monitor: check_port',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.ops_tools.monitoring.health',
  'qualname': 'check_port',
  'schema': {'type': 'function',
             'function': {'name': 'check_port',
                          'description': 'Checks whether a TCP port is open on a host. Use to '
                                         'verify if a service is running and reachable.',
                          'parameters': {'type': 'object',
                                         'properties': {'host': {'type': 'string',
                                                                 'description': 'Hostname or IP '
                                                                                'address to '
                                                                                'check.'},
                                                        'port': {'type': 'integer',
                                                                 'description': 'Port number to '
                                                                                'test.'},
                                                        'timeout': {'type': 'integer',
                                                                    'description': 'Connection '
                                                                                   'timeout in '
                                                                                   'seconds '
                                                                                   '(default: '
                                                                                   '3).'}},
                                         'required': ['host', 'port']}}}},
 {'name': 'classify_code',
  'category': 'development',
  'description': 'Dev: classify_code',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.dev_tools',
  'qualname': 'classify_code',
  'schema': {'type': 'function',
             'function': {'name': 'classify_code',
                          'description': 'Classifies a code file by type, language, and purpose '
                                         'using NLP analysis (e.g. "REST API handler", "data '
                                         'model", "utility").',
                          'parameters': {'type': 'object',
                                         'properties': {'file_path': {'type': 'string',
                                                                      'description': 'Path to the '
                                                                                     'source file '
                                                                                     'to '
                                                                                     'classify.'}},
                                         'required': ['file_path']}}}},
 {'name': 'code_agent_schemas_for_categories',
  'category': 'development',
  'description': 'Agent: schemas_for_categories',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.agents.specialized_agents._tool_schema',
  'qualname': 'schemas_for_categories',
  'schema': {'type': 'function',
             'function': {'name': 'code_agent_schemas_for_categories',
                          'description': 'Return OpenAI-style tool schemas for all tools in '
                                         '*categories*.',
                          'parameters': {'type': 'object',
                                         'properties': {'categories': {'type': 'string',
                                                                       'description': 'ToolCategory '
                                                                                      'values to '
                                                                                      'include.'},
                                                        'extra_names': {'type': 'string',
                                                                        'description': 'Additional '
                                                                                       'tool names '
                                                                                       'to add '
                                                                                       'regardless '
                                                                                       'of '
                                                                                       'category.'},
                                                        'exclude_names': {'type': 'string',
                                                                          'description': 'Tool '
                                                                                         'names to '
                                                                                         'suppress '
                                                                                         'from the '
                                                                                         'final '
                                                                                         'list.'}},
                                         'required': ['categories']}}}},
 {'name': 'codebase_search',
  'category': 'development',
  'description': 'Codebase: codebase_search',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.codebase_tools',
  'qualname': 'codebase_search',
  'schema': {'type': 'function',
             'function': {'name': 'codebase_search',
                          'description': 'Fast text/regex/symbol search across multiple files in a '
                                         'directory.',
                          'parameters': {'type': 'object',
                                         'properties': {'query': {'type': 'string',
                                                                  'description': 'Search string or '
                                                                                 'regex (e.g. "def '
                                                                                 'authenticate", '
                                                                                 '"class.*Service").'},
                                                        'path': {'type': 'string',
                                                                 'description': 'Root directory '
                                                                                'for search. '
                                                                                'Default ".".'},
                                                        'filters': {'type': 'string',
                                                                    'description': 'Optional dict '
                                                                                   'with '
                                                                                   'file_extensions, '
                                                                                   'exclude_dirs,'},
                                                        'max_results': {'type': 'integer',
                                                                        'description': 'Maximum '
                                                                                       'results to '
                                                                                       'return. '
                                                                                       'Default '
                                                                                       '50.'}},
                                         'required': ['query']}}}},
 {'name': 'compare_project_fronts',
  'category': 'development',
  'description': 'Codebase: compare_project_fronts',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.project_insights',
  'qualname': 'compare_project_fronts',
  'schema': {'type': 'function',
             'function': {'name': 'compare_project_fronts',
                          'description': 'Compare different project fronts, identifying '
                                         'similarities and patterns.',
                          'parameters': {'type': 'object',
                                         'properties': {'project_path': {'type': 'string',
                                                                         'description': 'Parâmetro '
                                                                                        'project_path'},
                                                        'fronts': {'type': 'string',
                                                                   'description': 'Parâmetro '
                                                                                  'fronts'}},
                                         'required': []}}}},
 {'name': 'create_checkpoint',
  'category': 'development',
  'description': 'Checkpoint: create_checkpoint',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.tools.checkpoint_tools',
  'qualname': 'create_checkpoint',
  'schema': {'type': 'function',
             'function': {'name': 'create_checkpoint',
                          'description': 'Create a checkpoint of the current project state.',
                          'parameters': {'type': 'object',
                                         'properties': {'description': {'type': 'string',
                                                                        'description': 'A brief '
                                                                                       'description '
                                                                                       'of what '
                                                                                       'the '
                                                                                       'checkpoint '
                                                                                       'captures'}},
                                         'required': []}}}},
 {'name': 'deep_project_analysis',
  'category': 'development',
  'description': 'Codebase: deep_project_analysis',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.tools.deep_analysis',
  'qualname': 'deep_project_analysis',
  'schema': {'type': 'function',
             'function': {'name': 'deep_project_analysis',
                          'description': 'Perform comprehensive deep analysis of a project.',
                          'parameters': {'type': 'object',
                                         'properties': {'path': {'type': 'string',
                                                                 'description': 'Project root '
                                                                                'path'},
                                                        'focus_areas': {'type': 'string',
                                                                        'description': 'Optional '
                                                                                       'list of '
                                                                                       'focus '
                                                                                       'areas:'},
                                                        'max_files': {'type': 'integer',
                                                                      'description': 'Maximum '
                                                                                     'files to '
                                                                                     'analyze in '
                                                                                     'depth'}},
                                         'required': []}}}},
 {'name': 'dep_analyze_import_graph',
  'category': 'development',
  'description': 'Dependency: analyze_import_graph',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.dependency_analysis',
  'qualname': 'analyze_import_graph',
  'schema': {'type': 'function',
             'function': {'name': 'dep_analyze_import_graph',
                          'description': 'Analyse the full import graph.',
                          'parameters': {'type': 'object',
                                         'properties': {'scope': {'type': 'string',
                                                                  'description': 'Parâmetro '
                                                                                 'scope'}},
                                         'required': []}}}},
 {'name': 'dep_find_dependencies',
  'category': 'development',
  'description': 'Dependency: find_dependencies',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.dependency_analysis',
  'qualname': 'find_dependencies',
  'schema': {'type': 'function',
             'function': {'name': 'dep_find_dependencies',
                          'description': 'Returns a list of files/modules that the given file '
                                         'directly imports or depends on.',
                          'parameters': {'type': 'object',
                                         'properties': {'file_path': {'type': 'string',
                                                                      'description': 'Path to the '
                                                                                     'file to '
                                                                                     'analyze.'},
                                                        'scope': {'type': 'string',
                                                                  'description': 'Root directory '
                                                                                 'to resolve '
                                                                                 'imports within '
                                                                                 '(default: '
                                                                                 'current dir).'}},
                                         'required': ['file_path']}}}},
 {'name': 'dep_find_dependents',
  'category': 'development',
  'description': 'Dependency: find_dependents',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.dependency_analysis',
  'qualname': 'find_dependents',
  'schema': {'type': 'function',
             'function': {'name': 'dep_find_dependents',
                          'description': 'Returns a list of files that import or depend on the '
                                         'given file.',
                          'parameters': {'type': 'object',
                                         'properties': {'file_path': {'type': 'string',
                                                                      'description': 'Path to the '
                                                                                     'file to '
                                                                                     'check.'},
                                                        'scope': {'type': 'string',
                                                                  'description': 'Root directory '
                                                                                 'to search within '
                                                                                 '(default: '
                                                                                 'current dir).'}},
                                         'required': ['file_path']}}}},
 {'name': 'deploy_check_deployment_health',
  'category': 'ci_cd',
  'description': 'CICD: check_deployment_health',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.ops_tools.ci_cd.deployment',
  'qualname': 'check_deployment_health',
  'schema': {'type': 'function',
             'function': {'name': 'deploy_check_deployment_health',
                          'description': 'Check the health of a deployment.',
                          'parameters': {'type': 'object',
                                         'properties': {'url': {'type': 'string',
                                                                'description': 'Parâmetro url'},
                                                        'timeout': {'type': 'integer',
                                                                    'description': 'Parâmetro '
                                                                                   'timeout'}},
                                         'required': ['url']}}}},
 {'name': 'deploy_deploy_application',
  'category': 'ci_cd',
  'description': 'CICD: deploy_application',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.ops_tools.ci_cd.deployment',
  'qualname': 'deploy_application',
  'schema': {'type': 'function',
             'function': {'name': 'deploy_deploy_application',
                          'description': 'Deploy an application using the given config.',
                          'parameters': {'type': 'object',
                                         'properties': {'config': {'type': 'string',
                                                                   'description': 'Parâmetro '
                                                                                  'config'},
                                                        'deployment_script': {'type': 'string',
                                                                              'description': 'Parâmetro '
                                                                                             'deployment_script'}},
                                         'required': ['config']}}}},
 {'name': 'deploy_get_deployment_status',
  'category': 'ci_cd',
  'description': 'CICD: get_deployment_status',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.ops_tools.ci_cd.deployment',
  'qualname': 'get_deployment_status',
  'schema': {'type': 'function',
             'function': {'name': 'deploy_get_deployment_status',
                          'description': 'Return the current deployment status.',
                          'parameters': {'type': 'object',
                                         'properties': {'deployment_id': {'type': 'string',
                                                                          'description': 'Parâmetro '
                                                                                         'deployment_id'}},
                                         'required': ['deployment_id']}}}},
 {'name': 'deploy_rollback_deployment',
  'category': 'ci_cd',
  'description': 'CICD: rollback_deployment',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.ops_tools.ci_cd.deployment',
  'qualname': 'rollback_deployment',
  'schema': {'type': 'function',
             'function': {'name': 'deploy_rollback_deployment',
                          'description': 'Faz rollback de um deployment.',
                          'parameters': {'type': 'object',
                                         'properties': {'deployment_id': {'type': 'string',
                                                                          'description': 'ID do '
                                                                                         'deployment'}},
                                         'required': ['deployment_id']}}}},
 {'name': 'diff_checkpoint',
  'category': 'development',
  'description': 'Checkpoint: diff_checkpoint',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.checkpoint_tools',
  'qualname': 'diff_checkpoint',
  'schema': {'type': 'function',
             'function': {'name': 'diff_checkpoint',
                          'description': 'Show differences between current state and a checkpoint.',
                          'parameters': {'type': 'object',
                                         'properties': {'checkpoint_id': {'type': 'string',
                                                                          'description': 'The ID '
                                                                                         'of the '
                                                                                         'checkpoint '
                                                                                         'to '
                                                                                         'compare '
                                                                                         'against'}},
                                         'required': ['checkpoint_id']}}}},
 {'name': 'discover_patterns',
  'category': 'development',
  'description': 'Codebase: discover_patterns',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.deep_analysis',
  'qualname': 'discover_patterns',
  'schema': {'type': 'function',
             'function': {'name': 'discover_patterns',
                          'description': 'Discover code patterns and conventions in a project.',
                          'parameters': {'type': 'object',
                                         'properties': {'path': {'type': 'string',
                                                                 'description': 'Project root '
                                                                                'path'},
                                                        'pattern_type': {'type': 'string',
                                                                         'description': 'Type of '
                                                                                        'patterns '
                                                                                        'to '
                                                                                        'discover:'}},
                                         'required': []}}}},
 {'name': 'docker_build',
  'category': 'docker',
  'description': 'Docker: docker_build',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.ops_tools.docker',
  'qualname': 'docker_build',
  'schema': {'type': 'function',
             'function': {'name': 'docker_build',
                          'description': 'Build a Docker image.',
                          'parameters': {'type': 'object',
                                         'properties': {'path': {'type': 'string',
                                                                 'description': 'Path to build '
                                                                                'context'},
                                                        'tag': {'type': 'string',
                                                                'description': 'Tag for the built '
                                                                               'image'},
                                                        'dockerfile': {'type': 'string',
                                                                       'description': 'Dockerfile '
                                                                                      'path '
                                                                                      '(relative '
                                                                                      'to '
                                                                                      'context)'},
                                                        'buildargs': {'type': 'string',
                                                                      'description': 'Build '
                                                                                     'arguments'},
                                                        'nocache': {'type': 'boolean',
                                                                    'description': "If True, don't "
                                                                                   'use cache'},
                                                        'pull': {'type': 'boolean',
                                                                 'description': 'If True, always '
                                                                                'pull base image'}},
                                         'required': ['path', 'tag']}}}},
 {'name': 'docker_compose',
  'category': 'docker',
  'description': 'Docker: docker_compose',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.ops_tools.docker',
  'qualname': 'docker_compose',
  'schema': {'type': 'function',
             'function': {'name': 'docker_compose',
                          'description': 'Execute docker-compose actions.',
                          'parameters': {'type': 'object',
                                         'properties': {'action': {'type': 'string',
                                                                   'description': 'Action to '
                                                                                  'perform (up, '
                                                                                  'down, restart, '
                                                                                  'ps, logs, '
                                                                                  'build)'},
                                                        'file': {'type': 'string',
                                                                 'description': 'Compose file '
                                                                                'path'},
                                                        'project_name': {'type': 'string',
                                                                         'description': 'Project '
                                                                                        'name '
                                                                                        'override'},
                                                        'services': {'type': 'string',
                                                                     'description': 'Specific '
                                                                                    'services to '
                                                                                    'target'}},
                                         'required': ['action']}}}},
 {'name': 'docker_exec',
  'category': 'docker',
  'description': 'Docker: docker_exec',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.ops_tools.docker',
  'qualname': 'docker_exec',
  'schema': {'type': 'function',
             'function': {'name': 'docker_exec',
                          'description': 'Execute a command inside a running container.',
                          'parameters': {'type': 'object',
                                         'properties': {'container': {'type': 'string',
                                                                      'description': 'Container '
                                                                                     'name or ID'},
                                                        'command': {'type': 'string',
                                                                    'description': 'Command to '
                                                                                   'execute '
                                                                                   '(string or '
                                                                                   'list)'},
                                                        'workdir': {'type': 'string',
                                                                    'description': 'Working '
                                                                                   'directory '
                                                                                   'inside '
                                                                                   'container'},
                                                        'user': {'type': 'string',
                                                                 'description': 'User to run '
                                                                                'command as'},
                                                        'environment': {'type': 'string',
                                                                        'description': 'Environment '
                                                                                       'variables'},
                                                        'detach': {'type': 'boolean',
                                                                   'description': 'If True, run in '
                                                                                  'background'}},
                                         'required': ['container', 'command']}}}},
 {'name': 'docker_images',
  'category': 'docker',
  'description': 'Docker: docker_images',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.ops_tools.docker',
  'qualname': 'docker_images',
  'schema': {'type': 'function',
             'function': {'name': 'docker_images',
                          'description': 'List Docker images.',
                          'parameters': {'type': 'object',
                                         'properties': {'name': {'type': 'string',
                                                                 'description': 'Filter by image '
                                                                                'name'},
                                                        'show_all': {'type': 'boolean',
                                                                     'description': 'If True, show '
                                                                                    'intermediate '
                                                                                    'images'}},
                                         'required': []}}}},
 {'name': 'docker_logs',
  'category': 'docker',
  'description': 'Docker: docker_logs',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.ops_tools.docker',
  'qualname': 'docker_logs',
  'schema': {'type': 'function',
             'function': {'name': 'docker_logs',
                          'description': 'Get logs from a container.',
                          'parameters': {'type': 'object',
                                         'properties': {'container': {'type': 'string',
                                                                      'description': 'Container '
                                                                                     'name or ID'},
                                                        'tail': {'type': 'integer',
                                                                 'description': 'Number of lines '
                                                                                'to show from end'},
                                                        'follow': {'type': 'boolean',
                                                                   'description': 'If True, stream '
                                                                                  'logs (returns '
                                                                                  'generator)'},
                                                        'timestamps': {'type': 'boolean',
                                                                       'description': 'If True, '
                                                                                      'include '
                                                                                      'timestamps'},
                                                        'since': {'type': 'string',
                                                                  'description': 'Show logs since '
                                                                                 'timestamp (e.g., '
                                                                                 '"2023-01-01", '
                                                                                 '"10m", "1h")'}},
                                         'required': ['container']}}}},
 {'name': 'docker_ps',
  'category': 'docker',
  'description': 'Docker: docker_ps',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.ops_tools.docker',
  'qualname': 'docker_ps',
  'schema': {'type': 'function',
             'function': {'name': 'docker_ps',
                          'description': 'List Docker containers.',
                          'parameters': {'type': 'object',
                                         'properties': {'show_all': {'type': 'boolean',
                                                                     'description': 'If True, list '
                                                                                    'all '
                                                                                    'containers '
                                                                                    '(including '
                                                                                    'stopped)'}},
                                         'required': []}}}},
 {'name': 'edit_file',
  'category': 'development',
  'description': 'Dev: edit_file',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.tools.dev_tools',
  'qualname': 'edit_file',
  'schema': {'type': 'function',
             'function': {'name': 'edit_file',
                          'description': 'Edit a file by replacing old_content with new_content '
                                         '(first occurrence).',
                          'parameters': {'type': 'object',
                                         'properties': {'path': {'type': 'string',
                                                                 'description': 'File to edit '
                                                                                '(relative or '
                                                                                'absolute).'},
                                                        'old_content': {'type': 'string',
                                                                        'description': 'Exact '
                                                                                       'string to '
                                                                                       'replace '
                                                                                       '(case-sensitive, '
                                                                                       'including '
                                                                                       'whitespace).'},
                                                        'new_content': {'type': 'string',
                                                                        'description': 'Replacement '
                                                                                       'string.'}},
                                         'required': ['path', 'old_content', 'new_content']}}}},
 {'name': 'enter_tangent_mode',
  'category': 'development',
  'description': 'Checkpoint: enter_tangent_mode',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.tools.checkpoint_tools',
  'qualname': 'enter_tangent_mode',
  'schema': {'type': 'function',
             'function': {'name': 'enter_tangent_mode',
                          'description': 'Enter tangent mode to explore an idea without affecting '
                                         'the main conversation.',
                          'parameters': {'type': 'object',
                                         'properties': {'conversation_history': {'type': 'string',
                                                                                 'description': 'Current '
                                                                                                'conversation '
                                                                                                'history '
                                                                                                'to '
                                                                                                'checkpoint'}},
                                         'required': []}}}},
 {'name': 'exit_tangent_mode',
  'category': 'development',
  'description': 'Checkpoint: exit_tangent_mode',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.tools.checkpoint_tools',
  'qualname': 'exit_tangent_mode',
  'schema': {'type': 'function',
             'function': {'name': 'exit_tangent_mode',
                          'description': 'Exit tangent mode and optionally restore the original '
                                         'conversation.',
                          'parameters': {'type': 'object',
                                         'properties': {'keep_tail': {'type': 'boolean',
                                                                      'description': 'If True, '
                                                                                     'keeps the '
                                                                                     'last Q&A '
                                                                                     'pair from '
                                                                                     'the tangent'},
                                                        'conversation_history': {'type': 'string',
                                                                                 'description': 'Parâmetro '
                                                                                                'conversation_history'}},
                                         'required': []}}}},
 {'name': 'extract_commit_message',
  'category': 'git',
  'description': 'Git: extract_commit_message',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.natural_git',
  'qualname': 'extract_commit_message',
  'schema': {'type': 'function',
             'function': {'name': 'extract_commit_message',
                          'description': 'Extract a commit message from a natural-language '
                                         'command.',
                          'parameters': {'type': 'object',
                                         'properties': {'command': {'type': 'string',
                                                                    'description': 'Parâmetro '
                                                                                   'command'}},
                                         'required': ['command']}}}},
 {'name': 'find_duplicate_code',
  'category': 'development',
  'description': 'Dev: find_duplicate_code',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.dev_tools',
  'qualname': 'find_duplicate_code',
  'schema': {'type': 'function',
             'function': {'name': 'find_duplicate_code',
                          'description': 'Find duplicate code using semantic similarity.',
                          'parameters': {'type': 'object',
                                         'properties': {'path': {'type': 'string',
                                                                 'description': 'Parâmetro path'},
                                                        'similarity_threshold': {'type': 'number',
                                                                                 'description': 'Parâmetro '
                                                                                                'similarity_threshold'}},
                                         'required': []}}}},
 {'name': 'find_in_files',
  'category': 'development',
  'description': 'Dev: find_in_files',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.dev_tools',
  'qualname': 'find_in_files',
  'schema': {'type': 'function',
             'function': {'name': 'find_in_files',
                          'description': 'Search for a pattern across project files.',
                          'parameters': {'type': 'object',
                                         'properties': {'pattern': {'type': 'string',
                                                                    'description': 'Parâmetro '
                                                                                   'pattern'},
                                                        'path': {'type': 'string',
                                                                 'description': 'Parâmetro path'},
                                                        'file_extensions': {'type': 'string',
                                                                            'description': 'Parâmetro '
                                                                                           'file_extensions'},
                                                        'max_results': {'type': 'integer',
                                                                        'description': 'Parâmetro '
                                                                                       'max_results'}},
                                         'required': ['pattern']}}}},
 {'name': 'forget_messages',
  'category': 'development',
  'description': 'Checkpoint: forget_messages',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.tools.checkpoint_tools',
  'qualname': 'forget_messages',
  'schema': {'type': 'function',
             'function': {'name': 'forget_messages',
                          'description': 'Remove recent messages from the conversation history.',
                          'parameters': {'type': 'object',
                                         'properties': {'count': {'type': 'integer',
                                                                  'description': 'Parâmetro count'},
                                                        'conversation_history': {'type': 'string',
                                                                                 'description': 'Parâmetro '
                                                                                                'conversation_history'}},
                                         'required': ['count']}}}},
 {'name': 'format_file',
  'category': 'development',
  'description': 'Forge: Format File',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.tools.nim_integration',
  'qualname': 'format_file',
  'schema': {'type': 'function',
             'function': {'name': 'format_file',
                          'description': 'Formats and lints a source file in-place using Aura '
                                         'Forge.',
                          'parameters': {'type': 'object',
                                         'properties': {'path': {'type': 'string',
                                                                 'description': 'Path to the file '
                                                                                'to format'}},
                                         'required': ['path']}}}},
 {'name': 'generate_tests_ml',
  'category': 'development',
  'description': 'Dev: generate_tests_ml',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.tools.dev_tools',
  'qualname': 'generate_tests_ml',
  'schema': {'type': 'function',
             'function': {'name': 'generate_tests_ml',
                          'description': 'Generate test cases using ML-based analysis.',
                          'parameters': {'type': 'object',
                                         'properties': {'file_path': {'type': 'string',
                                                                      'description': 'Parâmetro '
                                                                                     'file_path'}},
                                         'required': ['file_path']}}}},
 {'name': 'get_context_usage',
  'category': 'development',
  'description': 'Checkpoint: get_context_usage',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.checkpoint_tools',
  'qualname': 'get_context_usage',
  'schema': {'type': 'function',
             'function': {'name': 'get_context_usage',
                          'description': 'Get current context window usage information.',
                          'parameters': {'type': 'object', 'properties': {}, 'required': []}}}},
 {'name': 'gh_create_workflow',
  'category': 'ci_cd',
  'description': 'CICD: create_workflow',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.ops_tools.ci_cd.github_actions',
  'qualname': 'create_workflow',
  'schema': {'type': 'function',
             'function': {'name': 'gh_create_workflow',
                          'description': 'Create a GitHub Actions workflow file.',
                          'parameters': {'type': 'object',
                                         'properties': {'workflow_name': {'type': 'string',
                                                                          'description': 'Parâmetro '
                                                                                         'workflow_name'},
                                                        'config': {'type': 'string',
                                                                   'description': 'Parâmetro '
                                                                                  'config'},
                                                        'path': {'type': 'string',
                                                                 'description': 'Parâmetro path'}},
                                         'required': ['workflow_name', 'config']}}}},
 {'name': 'gh_get_workflow_status',
  'category': 'ci_cd',
  'description': 'CICD: get_workflow_status',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.ops_tools.ci_cd.github_actions',
  'qualname': 'get_workflow_status',
  'schema': {'type': 'function',
             'function': {'name': 'gh_get_workflow_status',
                          'description': 'Return the status of one or all workflows.',
                          'parameters': {'type': 'object',
                                         'properties': {'workflow_name': {'type': 'string',
                                                                          'description': 'Parâmetro '
                                                                                         'workflow_name'}},
                                         'required': []}}}},
 {'name': 'gh_list_workflows',
  'category': 'ci_cd',
  'description': 'CICD: list_workflows',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.ops_tools.ci_cd.github_actions',
  'qualname': 'list_workflows',
  'schema': {'type': 'function',
             'function': {'name': 'gh_list_workflows',
                          'description': 'Return a list of existing workflows.',
                          'parameters': {'type': 'object',
                                         'properties': {'path': {'type': 'string',
                                                                 'description': 'Parâmetro path'}},
                                         'required': []}}}},
 {'name': 'gh_run_workflow',
  'category': 'ci_cd',
  'description': 'CICD: run_workflow',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.ops_tools.ci_cd.github_actions',
  'qualname': 'run_workflow',
  'schema': {'type': 'function',
             'function': {'name': 'gh_run_workflow',
                          'description': 'Trigger a workflow run via GitHub CLI.',
                          'parameters': {'type': 'object',
                                         'properties': {'workflow_name': {'type': 'string',
                                                                          'description': 'Parâmetro '
                                                                                         'workflow_name'},
                                                        'ref': {'type': 'string',
                                                                'description': 'Parâmetro ref'},
                                                        'inputs': {'type': 'string',
                                                                   'description': 'Parâmetro '
                                                                                  'inputs'}},
                                         'required': ['workflow_name']}}}},
 {'name': 'git_branch',
  'category': 'git',
  'description': 'Git: git_branch',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.ops_tools.git',
  'qualname': 'git_branch',
  'schema': {'type': 'function',
             'function': {'name': 'git_branch',
                          'description': 'List all local and remote branches.',
                          'parameters': {'type': 'object', 'properties': {}, 'required': []}}}},
 {'name': 'git_commit',
  'category': 'git',
  'description': 'Git: git_commit',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.ops_tools.git',
  'qualname': 'git_commit',
  'schema': {'type': 'function',
             'function': {'name': 'git_commit',
                          'description': 'Create a git commit.',
                          'parameters': {'type': 'object',
                                         'properties': {'message': {'type': 'string',
                                                                    'description': 'Parâmetro '
                                                                                   'message'},
                                                        'files': {'type': 'string',
                                                                  'description': 'Parâmetro '
                                                                                 'files'}},
                                         'required': ['message']}}}},
 {'name': 'git_diff',
  'category': 'git',
  'description': 'Git: git_diff',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.ops_tools.git',
  'qualname': 'git_diff',
  'schema': {'type': 'function',
             'function': {'name': 'git_diff',
                          'description': 'Show git diff.',
                          'parameters': {'type': 'object',
                                         'properties': {'file': {'type': 'string',
                                                                 'description': 'Parâmetro file'},
                                                        'staged': {'type': 'boolean',
                                                                   'description': 'Parâmetro '
                                                                                  'staged'}},
                                         'required': []}}}},
 {'name': 'git_log',
  'category': 'git',
  'description': 'Git: git_log',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.ops_tools.git',
  'qualname': 'git_log',
  'schema': {'type': 'function',
             'function': {'name': 'git_log',
                          'description': 'Show recent git commits.',
                          'parameters': {'type': 'object',
                                         'properties': {'limit': {'type': 'integer',
                                                                  'description': 'Parâmetro '
                                                                                 'limit'}},
                                         'required': []}}}},
 {'name': 'git_status',
  'category': 'git',
  'description': 'Git: git_status',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.ops_tools.git',
  'qualname': 'git_status',
  'schema': {'type': 'function',
             'function': {'name': 'git_status',
                          'description': 'Show git working tree status.',
                          'parameters': {'type': 'object', 'properties': {}, 'required': []}}}},
 {'name': 'glob_search',
  'category': 'development',
  'description': 'Codebase: glob_search',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.codebase_tools',
  'qualname': 'glob_search',
  'schema': {'type': 'function',
             'function': {'name': 'glob_search',
                          'description': 'Finds files matching a glob pattern recursively. Faster '
                                         'than grep for locating files by name/extension.',
                          'parameters': {'type': 'object',
                                         'properties': {'pattern': {'type': 'string',
                                                                    'description': 'Glob pattern '
                                                                                   'to match (e.g. '
                                                                                   "'**/*.py', "
                                                                                   "'**/*test*.py')."},
                                                        'path': {'type': 'string',
                                                                 'description': 'Root directory to '
                                                                                'search from '
                                                                                '(default: current '
                                                                                'dir).'},
                                                        'exclude': {'type': 'string',
                                                                    'description': 'List of glob '
                                                                                   'patterns to '
                                                                                   'exclude from '
                                                                                   'results.'}},
                                         'required': ['pattern']}}}},
 {'name': 'inspect_code_structure',
  'category': 'development',
  'description': 'Codebase: inspect_code_structure',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.codebase_tools',
  'qualname': 'inspect_code_structure',
  'schema': {'type': 'function',
             'function': {'name': 'inspect_code_structure',
                          'description': 'Inspect the semantic structure of a code file using '
                                         'Prism.',
                          'parameters': {'type': 'object',
                                         'properties': {'file_path': {'type': 'string',
                                                                      'description': 'Parâmetro '
                                                                                     'file_path'},
                                                        'max_chunk_size': {'type': 'integer',
                                                                           'description': 'Parâmetro '
                                                                                          'max_chunk_size'}},
                                         'required': ['file_path']}}}},
 {'name': 'investigate_codebase',
  'category': 'development',
  'description': 'Codebase: investigate_codebase',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.tools.codebase_analysis',
  'qualname': 'investigate_codebase',
  'schema': {'type': 'function',
             'function': {'name': 'investigate_codebase',
                          'description': 'Deep, structured analysis of an entire codebase '
                                         'directory.',
                          'parameters': {'type': 'object',
                                         'properties': {'root_path': {'type': 'string',
                                                                      'description': 'Parâmetro '
                                                                                     'root_path'},
                                                        'objective': {'type': 'string',
                                                                      'description': 'Parâmetro '
                                                                                     'objective'},
                                                        'include_extensions': {'type': 'string',
                                                                               'description': 'Parâmetro '
                                                                                              'include_extensions'},
                                                        'max_files': {'type': 'integer',
                                                                      'description': 'Parâmetro '
                                                                                     'max_files'},
                                                        'verbose': {'type': 'boolean',
                                                                    'description': 'Parâmetro '
                                                                                   'verbose'},
                                                        'respect_gitignore': {'type': 'boolean',
                                                                              'description': 'Parâmetro '
                                                                                             'respect_gitignore'},
                                                        'use_imagination': {'type': 'boolean',
                                                                            'description': 'Parâmetro '
                                                                                           'use_imagination'}},
                                         'required': ['root_path']}}}},
 {'name': 'list_checkpoints',
  'category': 'development',
  'description': 'Checkpoint: list_checkpoints',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.checkpoint_tools',
  'qualname': 'list_checkpoints',
  'schema': {'type': 'function',
             'function': {'name': 'list_checkpoints',
                          'description': 'List all available checkpoints.',
                          'parameters': {'type': 'object', 'properties': {}, 'required': []}}}},
 {'name': 'list_directory',
  'category': 'file_system',
  'description': 'File system: list_directory',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.file_system',
  'qualname': 'list_directory',
  'schema': {'type': 'function',
             'function': {'name': 'list_directory',
                          'description': 'List the contents of a directory within the allowed '
                                         'workspace.',
                          'parameters': {'type': 'object',
                                         'properties': {'path': {'type': 'string',
                                                                 'description': 'Parâmetro path'},
                                                        'show_hidden': {'type': 'string',
                                                                        'description': 'Parâmetro '
                                                                                       'show_hidden'}},
                                         'required': ['path']}}}},
 {'name': 'llm_compare_model_responses',
  'category': 'development',
  'description': 'LLM: compare_model_responses',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.llm.multi_model',
  'qualname': 'compare_model_responses',
  'schema': {'type': 'function',
             'function': {'name': 'llm_compare_model_responses',
                          'description': 'Compare responses from different models and rank them.',
                          'parameters': {'type': 'object',
                                         'properties': {'prompt': {'type': 'string',
                                                                   'description': 'Parâmetro '
                                                                                  'prompt'},
                                                        'models': {'type': 'string',
                                                                   'description': 'Parâmetro '
                                                                                  'models'},
                                                        'system_message': {'type': 'string',
                                                                           'description': 'Parâmetro '
                                                                                          'system_message'}},
                                         'required': ['prompt']}}}},
 {'name': 'llm_get_default_multi_model_candidates',
  'category': 'development',
  'description': 'LLM: get_default_multi_model_candidates',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.llm.model_utils',
  'qualname': 'get_default_multi_model_candidates',
  'schema': {'type': 'function',
             'function': {'name': 'llm_get_default_multi_model_candidates',
                          'description': 'Return the canonical default ensemble list for '
                                         'multi-model mode.',
                          'parameters': {'type': 'object', 'properties': {}, 'required': []}}}},
 {'name': 'llm_normalize_model_name',
  'category': 'development',
  'description': 'LLM: normalize_model_name',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.llm.model_utils',
  'qualname': 'normalize_model_name',
  'schema': {'type': 'function',
             'function': {'name': 'llm_normalize_model_name',
                          'description': 'Normalise a model name to a canonical LiteLLM format.',
                          'parameters': {'type': 'object',
                                         'properties': {'model': {'type': 'string',
                                                                  'description': 'Parâmetro '
                                                                                 'model'}},
                                         'required': ['model']}}}},
 {'name': 'llm_query_multiple_models',
  'category': 'development',
  'description': 'LLM: query_multiple_models',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.llm.multi_model',
  'qualname': 'query_multiple_models',
  'schema': {'type': 'function',
             'function': {'name': 'llm_query_multiple_models',
                          'description': 'Query multiple models in parallel and return all '
                                         'responses.',
                          'parameters': {'type': 'object',
                                         'properties': {'prompt': {'type': 'string',
                                                                   'description': 'Parâmetro '
                                                                                  'prompt'},
                                                        'models': {'type': 'string',
                                                                   'description': 'Parâmetro '
                                                                                  'models'},
                                                        'system_message': {'type': 'string',
                                                                           'description': 'Parâmetro '
                                                                                          'system_message'}},
                                         'required': ['prompt']}}}},
 {'name': 'llm_smart_model_query',
  'category': 'development',
  'description': 'LLM: smart_model_query',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.llm.multi_model',
  'qualname': 'smart_model_query',
  'schema': {'type': 'function',
             'function': {'name': 'llm_smart_model_query',
                          'description': 'Execute a smart query with automatic model selection.',
                          'parameters': {'type': 'object',
                                         'properties': {'prompt': {'type': 'string',
                                                                   'description': 'Parâmetro '
                                                                                  'prompt'},
                                                        'models': {'type': 'string',
                                                                   'description': 'Parâmetro '
                                                                                  'models'},
                                                        'system_message': {'type': 'string',
                                                                           'description': 'Parâmetro '
                                                                                          'system_message'},
                                                        'ensemble_strategy': {'type': 'string',
                                                                              'description': 'Parâmetro '
                                                                                             'ensemble_strategy'}},
                                         'required': ['prompt']}}}},
 {'name': 'notebook_list',
  'category': 'development',
  'description': 'Notebook: List Pages',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.nim_integration',
  'qualname': 'notebook_list',
  'schema': {'type': 'function',
             'function': {'name': 'notebook_list',
                          'description': 'Lists all pages in the current Notebook session.',
                          'parameters': {'type': 'object', 'properties': {}, 'required': []}}}},
 {'name': 'notebook_read',
  'category': 'development',
  'description': 'Notebook: Read Memory',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.nim_integration',
  'qualname': 'notebook_read',
  'schema': {'type': 'function',
             'function': {'name': 'notebook_read',
                          'description': 'Reads a previously saved Notebook page and returns its '
                                         'content. Use after notebook_list to retrieve stored '
                                         'context.',
                          'parameters': {'type': 'object',
                                         'properties': {'page_path': {'type': 'string',
                                                                      'description': 'Path to the '
                                                                                     'page file '
                                                                                     '(as returned '
                                                                                     'by '
                                                                                     'notebook_write '
                                                                                     'or '
                                                                                     'notebook_list).'}},
                                         'required': ['page_path']}}}},
 {'name': 'notebook_search',
  'category': 'development',
  'description': 'Notebook: Search Memory',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.nim_integration',
  'qualname': 'notebook_search',
  'schema': {'type': 'function',
             'function': {'name': 'notebook_search',
                          'description': 'Searches the Notebook index (and potentially content) '
                                         'for keywords.',
                          'parameters': {'type': 'object',
                                         'properties': {'query': {'type': 'string',
                                                                  'description': 'Parâmetro '
                                                                                 'query'}},
                                         'required': ['query']}}}},
 {'name': 'notebook_write',
  'category': 'development',
  'description': 'Notebook: Write Memory',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.tools.nim_integration',
  'qualname': 'notebook_write',
  'schema': {'type': 'function',
             'function': {'name': 'notebook_write',
                          'description': "Writes a new page to the agent's persistent Notebook "
                                         'memory.',
                          'parameters': {'type': 'object',
                                         'properties': {'content': {'type': 'string',
                                                                    'description': 'The detailed '
                                                                                   'content to '
                                                                                   'save'},
                                                        'summary': {'type': 'string',
                                                                    'description': 'A one-line '
                                                                                   'summary for '
                                                                                   'the index'}},
                                         'required': ['content']}}}},
 {'name': 'paint_generate_art',
  'category': 'development',
  'description': 'Paint: paint_generate_art',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.tools.paint_tools',
  'qualname': 'paint_generate_art',
  'schema': {'type': 'function',
             'function': {'name': 'paint_generate_art',
                          'description': 'Paint: paint_generate_art',
                          'parameters': {'type': 'object',
                                         'properties': {'prompt': {'type': 'string',
                                                                   'description': 'Description of '
                                                                                  'art to generate '
                                                                                  "(e.g., 'a cat', "
                                                                                  "'ASCII art of a "
                                                                                  "house')"},
                                                        'width': {'type': 'integer',
                                                                  'description': 'Canvas width in '
                                                                                 'characters',
                                                                  'default': 80},
                                                        'height': {'type': 'integer',
                                                                   'description': 'Canvas height '
                                                                                  'in characters',
                                                                   'default': 24},
                                                        'output_file': {'type': 'string',
                                                                        'description': 'Optional '
                                                                                       'file path '
                                                                                       'to save '
                                                                                       'result. If '
                                                                                       'not '
                                                                                       'provided, '
                                                                                       'saves to '
                                                                                       "'artes/' "
                                                                                       'directory'},
                                                        'output_format': {'type': 'string',
                                                                          'enum': ['ans',
                                                                                   'png',
                                                                                   'svg',
                                                                                   'html'],
                                                                          'description': 'Output '
                                                                                         'format: '
                                                                                         "'ans' "
                                                                                         '(ANSI), '
                                                                                         "'png', "
                                                                                         "'svg', "
                                                                                         'or '
                                                                                         "'html'",
                                                                          'default': 'ans'},
                                                        'mode': {'type': 'string',
                                                                 'enum': ['auto',
                                                                          'ascii',
                                                                          'primitives',
                                                                          'hybrid'],
                                                                 'description': 'Generation mode: '
                                                                                "'auto' (LLM "
                                                                                'decides), '
                                                                                "'ascii', "
                                                                                "'primitives', or "
                                                                                "'hybrid'",
                                                                 'default': 'auto'}},
                                         'required': ['prompt']}}}},
 {'name': 'parse_natural_git_command',
  'category': 'git',
  'description': 'Git: parse_natural_git_command',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.tools.natural_git',
  'qualname': 'parse_natural_git_command',
  'schema': {'type': 'function',
             'function': {'name': 'parse_natural_git_command',
                          'description': 'Parse a natural-language Git command into a Git action '
                                         'dict.',
                          'parameters': {'type': 'object',
                                         'properties': {'command': {'type': 'string',
                                                                    'description': 'Natural-language '
                                                                                   'description '
                                                                                   '(e.g. "far '
                                                                                   'commit '
                                                                                   'changes").'}},
                                         'required': ['command']}}}},
 {'name': 'plan_build_edit_plan',
  'category': 'development',
  'description': 'Plan: build_edit_plan',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.application.editing.planning',
  'qualname': 'build_edit_plan',
  'schema': {'type': 'function',
             'function': {'name': 'plan_build_edit_plan',
                          'description': 'Normalize operation inputs and build a deterministic '
                                         'edit plan.',
                          'parameters': {'type': 'object',
                                         'properties': {'description': {'type': 'string',
                                                                        'description': 'Parâmetro '
                                                                                       'description'},
                                                        'operations': {'type': 'string',
                                                                       'description': 'Parâmetro '
                                                                                      'operations'},
                                                        'strategy': {'type': 'string',
                                                                     'description': 'Parâmetro '
                                                                                    'strategy'},
                                                        'id_factory': {'type': 'string',
                                                                       'description': 'Parâmetro '
                                                                                      'id_factory'}},
                                         'required': ['description', 'operations']}}}},
 {'name': 'plan_estimate_edit_risk',
  'category': 'development',
  'description': 'Plan: estimate_edit_risk',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.application.editing.planning',
  'qualname': 'estimate_edit_risk',
  'schema': {'type': 'function',
             'function': {'name': 'plan_estimate_edit_risk',
                          'description': 'Estimate risk from edit volume, critical filenames and '
                                         'dependency depth.',
                          'parameters': {'type': 'object',
                                         'properties': {'operations': {'type': 'string',
                                                                       'description': 'Parâmetro '
                                                                                      'operations'}},
                                         'required': ['operations']}}}},
 {'name': 'plan_order_edit_operations',
  'category': 'development',
  'description': 'Plan: order_edit_operations',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.application.editing.planning',
  'qualname': 'order_edit_operations',
  'schema': {'type': 'function',
             'function': {'name': 'plan_order_edit_operations',
                          'description': 'Order operations topologically, retaining '
                                         'cyclic/unresolved items at the end.',
                          'parameters': {'type': 'object',
                                         'properties': {'operations': {'type': 'string',
                                                                       'description': 'Parâmetro '
                                                                                      'operations'}},
                                         'required': ['operations']}}}},
 {'name': 'plan_refactoring',
  'category': 'development',
  'description': 'Refactor: plan_refactoring',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.refactoring.refactoring_planner',
  'qualname': 'plan_refactoring',
  'schema': {'type': 'function',
             'function': {'name': 'plan_refactoring',
                          'description': 'Creates a refactoring plan for a regex pattern '
                                         'replacement across the codebase, without executing it.',
                          'parameters': {'type': 'object',
                                         'properties': {'pattern': {'type': 'string',
                                                                    'description': 'Regex pattern '
                                                                                   'to find (e.g. '
                                                                                   "r'old_function_name')."},
                                                        'replacement': {'type': 'string',
                                                                        'description': 'Replacement '
                                                                                       'string.'},
                                                        'scope': {'type': 'string',
                                                                  'description': 'Root directory '
                                                                                 'to search '
                                                                                 '(default: '
                                                                                 'current dir).'},
                                                        'strategy': {'type': 'string',
                                                                     'description': 'Execution '
                                                                                    'strategy — '
                                                                                    "'incremental', "
                                                                                    "'all_at_once', "
                                                                                    'or '
                                                                                    "'by_dependency'."},
                                                        'file_pattern': {'type': 'string',
                                                                         'description': 'Glob '
                                                                                        'pattern '
                                                                                        'to filter '
                                                                                        'files '
                                                                                        '(default: '
                                                                                        "'*.py')."},
                                                        'max_results': {'type': 'integer',
                                                                        'description': 'Maximum '
                                                                                       'number of '
                                                                                       'matches to '
                                                                                       'include in '
                                                                                       'the '
                                                                                       'plan.'}},
                                         'required': ['pattern', 'replacement']}}}},
 {'name': 'process_info',
  'category': 'monitoring',
  'description': 'Monitor: process_info',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.ops_tools.monitoring.health',
  'qualname': 'process_info',
  'schema': {'type': 'function',
             'function': {'name': 'process_info',
                          'description': 'Lists running processes with PID, CPU%, and memory%. '
                                         'Filter by name to find a specific service.',
                          'parameters': {'type': 'object',
                                         'properties': {'name': {'type': 'string',
                                                                 'description': 'Process name to '
                                                                                'filter by (None = '
                                                                                'show all '
                                                                                'processes).'}},
                                         'required': []}}}},
 {'name': 'query_llm',
  'category': 'development',
  'description': 'LLM: query with fallback',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.llm.base',
  'qualname': 'query_with_fallback',
  'schema': {'type': 'function',
             'function': {'name': 'query_llm',
                          'description': 'Query an LLM with automatic per-provider fallback and '
                                         'exponential-backoff retry.',
                          'parameters': {'type': 'object',
                                         'properties': {'model': {'type': 'string',
                                                                  'description': 'Primary model '
                                                                                 'name (LiteLLM '
                                                                                 'format).'},
                                                        'messages': {'type': 'string',
                                                                     'description': 'Chat messages '
                                                                                    'list, each '
                                                                                    'with "role" '
                                                                                    'and '
                                                                                    '"content".'},
                                                        'fallback_models': {'type': 'string',
                                                                            'description': 'Custom '
                                                                                           'fallback '
                                                                                           'list; '
                                                                                           'overrides '
                                                                                           'MODEL_PRESETS '
                                                                                           'when '
                                                                                           'set.'},
                                                        'max_retries': {'type': 'integer',
                                                                        'description': 'Attempts '
                                                                                       'per model '
                                                                                       'before '
                                                                                       'moving to '
                                                                                       'the next.'},
                                                        'timeout': {'type': 'number',
                                                                    'description': 'Per-request '
                                                                                   'timeout in '
                                                                                   'seconds.'},
                                                        'tools': {'type': 'string',
                                                                  'description': 'Optional '
                                                                                 'function-calling '
                                                                                 'tool list '
                                                                                 '(OpenAI '
                                                                                 'format).'},
                                                        'cross_provider_fallback': {'type': 'boolean',
                                                                                    'description': 'If '
                                                                                                   'True, '
                                                                                                   'allows '
                                                                                                   'falling '
                                                                                                   'back '
                                                                                                   'across '
                                                                                                   'providers.'},
                                                        'event_callback': {'type': 'string',
                                                                           'description': 'Parâmetro '
                                                                                          'event_callback'}},
                                         'required': ['model', 'messages']}}}},
 {'name': 'read_file',
  'category': 'file_system',
  'description': 'File system: read_file',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.file_system',
  'qualname': 'read_file',
  'schema': {'type': 'function',
             'function': {'name': 'read_file',
                          'description': 'Read a file (or partial range) and return its content as '
                                         'a string.',
                          'parameters': {'type': 'object',
                                         'properties': {'path': {'type': 'string',
                                                                 'description': 'Path to the file '
                                                                                '(relative or '
                                                                                'absolute). Not a '
                                                                                'directory —'},
                                                        'offset': {'type': 'string',
                                                                   'description': 'Starting line '
                                                                                  '(0-indexed). '
                                                                                  'Default 0.'},
                                                        'limit': {'type': 'string',
                                                                  'description': 'Number of lines '
                                                                                 'to read from '
                                                                                 'offset. -1 reads '
                                                                                 'to end of '
                                                                                 'file.'}},
                                         'required': ['path']}}}},
 {'name': 'refactor_agent_schemas_for_categories',
  'category': 'development',
  'description': 'Agent: schemas_for_categories',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.agents.specialized_agents._tool_schema',
  'qualname': 'schemas_for_categories',
  'schema': {'type': 'function',
             'function': {'name': 'refactor_agent_schemas_for_categories',
                          'description': 'Return OpenAI-style tool schemas for all tools in '
                                         '*categories*.',
                          'parameters': {'type': 'object',
                                         'properties': {'categories': {'type': 'string',
                                                                       'description': 'ToolCategory '
                                                                                      'values to '
                                                                                      'include.'},
                                                        'extra_names': {'type': 'string',
                                                                        'description': 'Additional '
                                                                                       'tool names '
                                                                                       'to add '
                                                                                       'regardless '
                                                                                       'of '
                                                                                       'category.'},
                                                        'exclude_names': {'type': 'string',
                                                                          'description': 'Tool '
                                                                                         'names to '
                                                                                         'suppress '
                                                                                         'from the '
                                                                                         'final '
                                                                                         'list.'}},
                                         'required': ['categories']}}}},
 {'name': 'restore_backup',
  'category': 'development',
  'description': 'Dev: restore_backup',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.tools.dev_tools',
  'qualname': 'restore_backup',
  'schema': {'type': 'function',
             'function': {'name': 'restore_backup',
                          'description': 'Restores a file from a previously created backup. Use '
                                         'after a failed edit to recover the original.',
                          'parameters': {'type': 'object',
                                         'properties': {'original_path': {'type': 'string',
                                                                          'description': 'Path of '
                                                                                         'the file '
                                                                                         'to '
                                                                                         'restore.'},
                                                        'backup_path': {'type': 'string',
                                                                        'description': 'Path to a '
                                                                                       'specific '
                                                                                       'backup '
                                                                                       'file (None '
                                                                                       '= use the '
                                                                                       'most '
                                                                                       'recent '
                                                                                       'backup).'}},
                                         'required': ['original_path']}}}},
 {'name': 'restore_checkpoint',
  'category': 'development',
  'description': 'Checkpoint: restore_checkpoint',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.tools.checkpoint_tools',
  'qualname': 'restore_checkpoint',
  'schema': {'type': 'function',
             'function': {'name': 'restore_checkpoint',
                          'description': 'Restore the workspace to a checkpoint.',
                          'parameters': {'type': 'object',
                                         'properties': {'checkpoint_id': {'type': 'string',
                                                                          'description': 'Parâmetro '
                                                                                         'checkpoint_id'},
                                                        'hard': {'type': 'boolean',
                                                                 'description': 'Parâmetro hard'}},
                                         'required': ['checkpoint_id']}}}},
 {'name': 'review_agent_schemas_for_categories',
  'category': 'development',
  'description': 'Agent: schemas_for_categories',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.agents.specialized_agents._tool_schema',
  'qualname': 'schemas_for_categories',
  'schema': {'type': 'function',
             'function': {'name': 'review_agent_schemas_for_categories',
                          'description': 'Return OpenAI-style tool schemas for all tools in '
                                         '*categories*.',
                          'parameters': {'type': 'object',
                                         'properties': {'categories': {'type': 'string',
                                                                       'description': 'ToolCategory '
                                                                                      'values to '
                                                                                      'include.'},
                                                        'extra_names': {'type': 'string',
                                                                        'description': 'Additional '
                                                                                       'tool names '
                                                                                       'to add '
                                                                                       'regardless '
                                                                                       'of '
                                                                                       'category.'},
                                                        'exclude_names': {'type': 'string',
                                                                          'description': 'Tool '
                                                                                         'names to '
                                                                                         'suppress '
                                                                                         'from the '
                                                                                         'final '
                                                                                         'list.'}},
                                         'required': ['categories']}}}},
 {'name': 'run_shell_command',
  'category': 'shell',
  'description': 'Shell: run_shell_command',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.tools.shell',
  'qualname': 'run_shell_command',
  'schema': {'type': 'function',
             'function': {'name': 'run_shell_command',
                          'description': 'Run a shell command with timeout and capture output.',
                          'parameters': {'type': 'object',
                                         'properties': {'command': {'type': 'string',
                                                                    'description': 'Parâmetro '
                                                                                   'command'},
                                                        'background': {'type': 'boolean',
                                                                       'description': 'Parâmetro '
                                                                                      'background'},
                                                        'owner_task': {'type': 'string',
                                                                       'description': 'Parâmetro '
                                                                                      'owner_task'}},
                                         'required': ['command']}}}},
 {'name': 'run_tests_advanced',
  'category': 'testing',
  'description': 'Test: run_tests_advanced',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.testing.test_runner',
  'qualname': 'run_tests',
  'schema': {'type': 'function',
             'function': {'name': 'run_tests_advanced',
                          'description': 'Runs tests related to a modified file, or a specific '
                                         'list of test files, or all tests in scope.',
                          'parameters': {'type': 'object',
                                         'properties': {'file_path': {'type': 'string',
                                                                      'description': 'Modified '
                                                                                     'source file '
                                                                                     '— '
                                                                                     'auto-discovers '
                                                                                     'related test '
                                                                                     'files.'},
                                                        'test_files': {'type': 'string',
                                                                       'description': 'Explicit '
                                                                                      'list of '
                                                                                      'test file '
                                                                                      'paths to '
                                                                                      'run '
                                                                                      '(overrides '
                                                                                      'auto-discovery).'},
                                                        'scope': {'type': 'string',
                                                                  'description': 'Project root to '
                                                                                 'search for tests '
                                                                                 '(default: '
                                                                                 'current dir).'}},
                                         'required': []}}}},
 {'name': 'sanitize_code',
  'category': 'development',
  'description': 'Forge: Code Sanitizer',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.tools.nim_integration',
  'qualname': 'sanitize_code',
  'schema': {'type': 'function',
             'function': {'name': 'sanitize_code',
                          'description': 'Safe-checks, lints, and formats code using Aura Forge '
                                         'sandbox.',
                          'parameters': {'type': 'object',
                                         'properties': {'code': {'type': 'string',
                                                                 'description': 'The source code '
                                                                                'to process'},
                                                        'fix': {'type': 'boolean',
                                                                'description': 'Whether to attempt '
                                                                               'automatic fixing '
                                                                               '(formatting, safe '
                                                                               'lint fixes)'}},
                                         'required': ['code']}}}},
 {'name': 'scan_project',
  'category': 'file_system',
  'description': 'Imagination: Fast Project Scanner',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.nim_integration',
  'qualname': 'scan_project',
  'schema': {'type': 'function',
             'function': {'name': 'scan_project',
                          'description': 'Scans the project directory structure using the '
                                         'high-performance Imagination Engine.',
                          'parameters': {'type': 'object',
                                         'properties': {'path': {'type': 'string',
                                                                 'description': 'Root path to scan '
                                                                                '(default: current '
                                                                                'directory)'},
                                                        'context': {'type': 'string',
                                                                    'description': 'Optional '
                                                                                   'keywords to '
                                                                                   'filter results '
                                                                                   'by relevance '
                                                                                   '(e.g. "auth '
                                                                                   'login")'},
                                                        'limit': {'type': 'integer',
                                                                  'description': 'Maximum number '
                                                                                 'of relevant '
                                                                                 'files to return '
                                                                                 'when using '
                                                                                 'context'}},
                                         'required': []}}}},
 {'name': 'semantic_search_advanced',
  'category': 'development',
  'description': 'Dev: semantic_search_advanced',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.tools.dev_tools',
  'qualname': 'semantic_search_advanced',
  'schema': {'type': 'function',
             'function': {'name': 'semantic_search_advanced',
                          'description': 'Advanced semantic search using HuggingFace embeddings.',
                          'parameters': {'type': 'object',
                                         'properties': {'query': {'type': 'string',
                                                                  'description': 'Parâmetro query'},
                                                        'index_id': {'type': 'string',
                                                                     'description': 'Parâmetro '
                                                                                    'index_id'},
                                                        'top_k': {'type': 'integer',
                                                                  'description': 'Parâmetro '
                                                                                 'top_k'}},
                                         'required': ['query']}}}},
 {'name': 'suggest_commit_message',
  'category': 'git',
  'description': 'Git: suggest_commit_message',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.tools.natural_git',
  'qualname': 'suggest_commit_message',
  'schema': {'type': 'function',
             'function': {'name': 'suggest_commit_message',
                          'description': 'Suggest a conventional-commits message based on changed '
                                         'files.',
                          'parameters': {'type': 'object',
                                         'properties': {'changes': {'type': 'string',
                                                                    'description': 'List of '
                                                                                   'git-status '
                                                                                   '--short '
                                                                                   'lines'}},
                                         'required': []}}}},
 {'name': 'summarize_code',
  'category': 'development',
  'description': 'Dev: summarize_code',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.dev_tools',
  'qualname': 'summarize_code',
  'schema': {'type': 'function',
             'function': {'name': 'summarize_code',
                          'description': 'Generates a natural-language summary of what a code file '
                                         'does, its main functions, and its role in the project.',
                          'parameters': {'type': 'object',
                                         'properties': {'file_path': {'type': 'string',
                                                                      'description': 'Path to the '
                                                                                     'source file '
                                                                                     'to '
                                                                                     'summarize.'}},
                                         'required': ['file_path']}}}},
 {'name': 'system_resources',
  'category': 'monitoring',
  'description': 'Monitor: system_resources',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.ops_tools.monitoring.health',
  'qualname': 'system_resources',
  'schema': {'type': 'function',
             'function': {'name': 'system_resources',
                          'description': 'Display system resources (CPU, RAM, Disk).',
                          'parameters': {'type': 'object', 'properties': {}, 'required': []}}}},
 {'name': 'test_agent_schemas_for_categories',
  'category': 'development',
  'description': 'Agent: schemas_for_categories',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.agents.specialized_agents._tool_schema',
  'qualname': 'schemas_for_categories',
  'schema': {'type': 'function',
             'function': {'name': 'test_agent_schemas_for_categories',
                          'description': 'Return OpenAI-style tool schemas for all tools in '
                                         '*categories*.',
                          'parameters': {'type': 'object',
                                         'properties': {'categories': {'type': 'string',
                                                                       'description': 'ToolCategory '
                                                                                      'values to '
                                                                                      'include.'},
                                                        'extra_names': {'type': 'string',
                                                                        'description': 'Additional '
                                                                                       'tool names '
                                                                                       'to add '
                                                                                       'regardless '
                                                                                       'of '
                                                                                       'category.'},
                                                        'exclude_names': {'type': 'string',
                                                                          'description': 'Tool '
                                                                                         'names to '
                                                                                         'suppress '
                                                                                         'from the '
                                                                                         'final '
                                                                                         'list.'}},
                                         'required': ['categories']}}}},
 {'name': 'todo_refresh_todo_tracker',
  'category': 'development',
  'description': 'Todo: refresh_todo_tracker',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.todo.todo_tracker',
  'qualname': 'refresh_todo_tracker',
  'schema': {'type': 'function',
             'function': {'name': 'todo_refresh_todo_tracker',
                          'description': 'Force a tracker refresh and return a new singleton.',
                          'parameters': {'type': 'object',
                                         'properties': {'scope': {'type': 'string',
                                                                  'description': 'Parâmetro '
                                                                                 'scope'}},
                                         'required': []}}}},
 {'name': 'tokenize_code',
  'category': 'development',
  'description': 'Dev: tokenize_code',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.dev_tools',
  'qualname': 'tokenize_code',
  'schema': {'type': 'function',
             'function': {'name': 'tokenize_code',
                          'description': 'Tokenise code using specialised HuggingFace models.',
                          'parameters': {'type': 'object',
                                         'properties': {'code': {'type': 'string',
                                                                 'description': 'Parâmetro code'},
                                                        'language': {'type': 'string',
                                                                     'description': 'Parâmetro '
                                                                                    'language'}},
                                         'required': ['code']}}}},
 {'name': 'tree_view',
  'category': 'development',
  'description': 'Dev: tree_view',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.dev_tools',
  'qualname': 'tree_view',
  'schema': {'type': 'function',
             'function': {'name': 'tree_view',
                          'description': 'Display a Linux-style directory tree.',
                          'parameters': {'type': 'object',
                                         'properties': {'path': {'type': 'string',
                                                                 'description': 'Parâmetro path'},
                                                        'max_depth': {'type': 'integer',
                                                                      'description': 'Parâmetro '
                                                                                     'max_depth'},
                                                        'show_hidden': {'type': 'boolean',
                                                                        'description': 'Parâmetro '
                                                                                       'show_hidden'}},
                                         'required': []}}}},
 {'name': 'validate_syntax',
  'category': 'development',
  'description': 'Dev: validate_syntax',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.dev_tools',
  'qualname': 'validate_syntax',
  'schema': {'type': 'function',
             'function': {'name': 'validate_syntax',
                          'description': 'Validate syntax for a code snippet or file.',
                          'parameters': {'type': 'object',
                                         'properties': {'content': {'type': 'string',
                                                                    'description': 'Parâmetro '
                                                                                   'content'},
                                                        'language': {'type': 'string',
                                                                     'description': 'Parâmetro '
                                                                                    'language'}},
                                         'required': ['content', 'language']}}}},
 {'name': 'view_repo_map',
  'category': 'development',
  'description': 'Codebase: view_repo_map',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.codebase_tools',
  'qualname': 'view_repo_map',
  'schema': {'type': 'function',
             'function': {'name': 'view_repo_map',
                          'description': 'Returns a plain-text directory tree of the repository, '
                                         'similar to the `tree` command.',
                          'parameters': {'type': 'object',
                                         'properties': {'depth': {'type': 'integer',
                                                                  'description': 'Maximum '
                                                                                 'directory depth '
                                                                                 'to traverse '
                                                                                 '(default: 3).'},
                                                        'path': {'type': 'string',
                                                                 'description': 'Root directory to '
                                                                                'start from '
                                                                                '(default: current '
                                                                                'dir).'}},
                                         'required': []}}}},
 {'name': 'view_subdirectory',
  'category': 'development',
  'description': 'Codebase: view_subdirectory',
  'effect': 'read_only',
  'cacheable': False,
  'module': 'aura_cli.core.tools.codebase_tools',
  'qualname': 'view_subdirectory',
  'schema': {'type': 'function',
             'function': {'name': 'view_subdirectory',
                          'description': 'Returns a plain-text directory tree for a specific '
                                         'subdirectory.',
                          'parameters': {'type': 'object',
                                         'properties': {'path': {'type': 'string',
                                                                 'description': 'Path to the '
                                                                                'subdirectory to '
                                                                                'inspect.'},
                                                        'max_depth': {'type': 'integer',
                                                                      'description': 'Maximum '
                                                                                     'depth to '
                                                                                     'traverse '
                                                                                     '(default: '
                                                                                     '2).'},
                                                        'show_files': {'type': 'boolean',
                                                                       'description': 'If True, '
                                                                                      'includes '
                                                                                      'files; if '
                                                                                      'False, '
                                                                                      'shows only '
                                                                                      'directories '
                                                                                      '(default: '
                                                                                      'True).'}},
                                         'required': ['path']}}}},
 {'name': 'viz_export_dependency_graph',
  'category': 'development',
  'description': 'Viz: export_dependency_graph',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.visualization.visualization',
  'qualname': 'export_dependency_graph',
  'schema': {'type': 'function',
             'function': {'name': 'viz_export_dependency_graph',
                          'description': 'Export a dependency graph to a file.',
                          'parameters': {'type': 'object',
                                         'properties': {'dependencies': {'type': 'string',
                                                                         'description': 'Parâmetro '
                                                                                        'dependencies'},
                                                        'output_path': {'type': 'string',
                                                                        'description': 'Parâmetro '
                                                                                       'output_path'},
                                                        'output_format': {'type': 'string',
                                                                          'description': 'Parâmetro '
                                                                                         'output_format'}},
                                         'required': ['dependencies', 'output_path']}}}},
 {'name': 'viz_export_impact_analysis',
  'category': 'development',
  'description': 'Viz: export_impact_analysis',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.visualization.visualization',
  'qualname': 'export_impact_analysis',
  'schema': {'type': 'function',
             'function': {'name': 'viz_export_impact_analysis',
                          'description': 'Export an impact analysis report to a file.',
                          'parameters': {'type': 'object',
                                         'properties': {'impact_data': {'type': 'string',
                                                                        'description': 'Parâmetro '
                                                                                       'impact_data'},
                                                        'output_path': {'type': 'string',
                                                                        'description': 'Parâmetro '
                                                                                       'output_path'},
                                                        'output_format': {'type': 'string',
                                                                          'description': 'Parâmetro '
                                                                                         'output_format'}},
                                         'required': ['impact_data', 'output_path']}}}},
 {'name': 'viz_visualize_dependency_graph',
  'category': 'development',
  'description': 'Viz: visualize_dependency_graph',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.visualization.visualization',
  'qualname': 'visualize_dependency_graph',
  'schema': {'type': 'function',
             'function': {'name': 'viz_visualize_dependency_graph',
                          'description': 'Visualise the dependency graph.',
                          'parameters': {'type': 'object',
                                         'properties': {'dependencies': {'type': 'string',
                                                                         'description': 'Parâmetro '
                                                                                        'dependencies'},
                                                        'root_nodes': {'type': 'string',
                                                                       'description': 'Parâmetro '
                                                                                      'root_nodes'},
                                                        'max_depth': {'type': 'integer',
                                                                      'description': 'Parâmetro '
                                                                                     'max_depth'},
                                                        'output_format': {'type': 'string',
                                                                          'description': 'Parâmetro '
                                                                                         'output_format'}},
                                         'required': ['dependencies']}}}},
 {'name': 'viz_visualize_impact_analysis',
  'category': 'development',
  'description': 'Viz: visualize_impact_analysis',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.visualization.visualization',
  'qualname': 'visualize_impact_analysis',
  'schema': {'type': 'function',
             'function': {'name': 'viz_visualize_impact_analysis',
                          'description': 'Visualise the impact analysis.',
                          'parameters': {'type': 'object',
                                         'properties': {'impact_data': {'type': 'string',
                                                                        'description': 'Parâmetro '
                                                                                       'impact_data'},
                                                        'output_format': {'type': 'string',
                                                                          'description': 'Parâmetro '
                                                                                         'output_format'}},
                                         'required': ['impact_data']}}}},
 {'name': 'viz_visualize_refactoring_progress',
  'category': 'development',
  'description': 'Viz: visualize_refactoring_progress',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.visualization.visualization',
  'qualname': 'visualize_refactoring_progress',
  'schema': {'type': 'function',
             'function': {'name': 'viz_visualize_refactoring_progress',
                          'description': 'Visualise refactoring progress.',
                          'parameters': {'type': 'object',
                                         'properties': {'plan': {'type': 'string',
                                                                 'description': 'Parâmetro plan'},
                                                        'completed_steps': {'type': 'integer',
                                                                            'description': 'Parâmetro '
                                                                                           'completed_steps'},
                                                        'total_steps': {'type': 'integer',
                                                                        'description': 'Parâmetro '
                                                                                       'total_steps'},
                                                        'current_batch': {'type': 'string',
                                                                          'description': 'Parâmetro '
                                                                                         'current_batch'},
                                                        'total_batches': {'type': 'string',
                                                                          'description': 'Parâmetro '
                                                                                         'total_batches'}},
                                         'required': ['plan', 'completed_steps', 'total_steps']}}}},
 {'name': 'web_search',
  'category': 'web',
  'description': 'Web: web_search',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.tools.web',
  'qualname': 'web_search',
  'schema': {'type': 'function',
             'function': {'name': 'web_search',
                          'description': 'Performs a web search and returns the top results.',
                          'parameters': {'type': 'object',
                                         'properties': {'query': {'type': 'string',
                                                                  'description': 'Parâmetro query'},
                                                        'num_results': {'type': 'integer',
                                                                        'description': 'Parâmetro '
                                                                                       'num_results'}},
                                         'required': ['query']}}}},
 {'name': 'write_file',
  'category': 'file_system',
  'description': 'File system: write_file',
  'effect': 'mutating',
  'cacheable': False,
  'module': 'aura_cli.core.tools.file_system',
  'qualname': 'write_file',
  'schema': {'type': 'function',
             'function': {'name': 'write_file',
                          'description': 'Write or append content to a file, requesting user '
                                         'confirmation first.',
                          'parameters': {'type': 'object',
                                         'properties': {'path': {'type': 'string',
                                                                 'description': 'File path '
                                                                                '(relative or '
                                                                                'absolute). Parent '
                                                                                'directory must '
                                                                                'exist.'},
                                                        'content': {'type': 'string',
                                                                    'description': 'Content to '
                                                                                   'write '
                                                                                   '(UTF-8).'},
                                                        'append': {'type': 'string',
                                                                   'description': 'If True, '
                                                                                  'appends to the '
                                                                                  'existing file. '
                                                                                  'If False '
                                                                                  '(default),'}},
                                         'required': ['path', 'content']}}}}]
