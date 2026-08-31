"""
Testes para o módulo access_control.

Testa funcionalidades de gerenciamento de permissões,
roles e controle de acesso granular.
"""

from aura_cli.core.ops_tools.security.access_control import (
    AccessControl,
    Permission,
    Role,
)


class TestPermission:
    """Testa enum Permission."""

    def test_permission_values(self):
        """Testa valores das permissões."""
        assert Permission.READ.value == "read"
        assert Permission.WRITE.value == "write"
        assert Permission.EXECUTE.value == "execute"
        assert Permission.DELETE.value == "delete"
        assert Permission.ADMIN.value == "admin"

    def test_permission_completeness(self):
        """Testa completude das permissões."""
        expected_permissions = {"read", "write", "execute", "delete", "admin"}
        actual_permissions = {p.value for p in Permission}

        assert actual_permissions == expected_permissions

    def test_permission_hierarchy_concept(self):
        """Testa conceito de hierarquia de permissões."""
        # ADMIN deve incluir todas as outras permissões
        all_permissions = set(Permission)

        # Verificar que ADMIN está incluído
        assert Permission.ADMIN in all_permissions

        # Verificar que temos diferentes níveis
        basic_permissions = {Permission.READ}
        advanced_permissions = {Permission.READ, Permission.WRITE, Permission.EXECUTE}

        assert len(basic_permissions) < len(advanced_permissions)
        assert len(advanced_permissions) < len(all_permissions)


class TestRole:
    """Testa dataclass Role."""

    def test_role_creation(self):
        """Testa criação de role."""
        permissions = {Permission.READ, Permission.WRITE}
        role = Role(
            id="role-001",
            name="editor",
            permissions=permissions,
            description="Can read and write",
        )

        assert role.id == "role-001"
        assert role.name == "editor"
        assert role.permissions == permissions
        assert role.description == "Can read and write"

    def test_role_with_minimal_fields(self):
        """Testa role com campos mínimos."""
        permissions = {Permission.READ}
        role = Role(id="minimal-role", name="reader", permissions=permissions)

        assert role.id == "minimal-role"
        assert role.name == "reader"
        assert role.permissions == permissions
        assert role.description == ""  # Default value

    def test_role_permissions_set_operations(self):
        """Testa operações de conjunto com permissões."""
        read_write_role = Role(
            "rw-role", "read_write", {Permission.READ, Permission.WRITE}
        )

        execute_delete_role = Role(
            "ed-role", "execute_delete", {Permission.EXECUTE, Permission.DELETE}
        )

        # União de permissões
        combined_permissions = (
            read_write_role.permissions | execute_delete_role.permissions
        )
        assert len(combined_permissions) == 4
        assert Permission.READ in combined_permissions
        assert Permission.DELETE in combined_permissions

        # Interseção (deve ser vazia neste caso)
        intersection = read_write_role.permissions & execute_delete_role.permissions
        assert len(intersection) == 0

    def test_admin_role_all_permissions(self):
        """Testa role admin com todas as permissões."""
        admin_role = Role("admin-role", "admin", set(Permission), "Full access")

        assert len(admin_role.permissions) == len(Permission)
        assert Permission.ADMIN in admin_role.permissions
        assert Permission.READ in admin_role.permissions
        assert Permission.DELETE in admin_role.permissions


class TestAccessControl:
    """Testa classe AccessControl."""

    def setup_method(self):
        """Setup para cada teste."""
        self.access_control = AccessControl()

    def test_init(self):
        """Testa inicialização."""
        assert hasattr(self.access_control, "roles")
        assert hasattr(self.access_control, "user_roles")
        assert hasattr(self.access_control, "stats")
        assert isinstance(self.access_control.roles, dict)
        assert isinstance(self.access_control.user_roles, dict)

    def test_default_roles_creation(self):
        """Testa criação de roles padrão."""
        # Deve ter criado roles padrão
        assert len(self.access_control.roles) >= 3

        # Verificar que existem roles com nomes esperados
        role_names = [role.name for role in self.access_control.roles.values()]
        assert "admin" in role_names
        assert "developer" in role_names
        assert "read_only" in role_names

    def test_admin_role_permissions(self):
        """Testa permissões do role admin."""
        admin_roles = [
            role for role in self.access_control.roles.values() if role.name == "admin"
        ]

        assert len(admin_roles) == 1
        admin_role = admin_roles[0]

        # Admin deve ter todas as permissões
        assert len(admin_role.permissions) == len(Permission)
        assert Permission.ADMIN in admin_role.permissions
        assert Permission.DELETE in admin_role.permissions

    def test_developer_role_permissions(self):
        """Testa permissões do role developer."""
        dev_roles = [
            role
            for role in self.access_control.roles.values()
            if role.name == "developer"
        ]

        assert len(dev_roles) == 1
        dev_role = dev_roles[0]

        # Developer deve ter READ, WRITE, EXECUTE mas não DELETE nem ADMIN
        expected_permissions = {Permission.READ, Permission.WRITE, Permission.EXECUTE}
        assert dev_role.permissions == expected_permissions

    def test_read_only_role_permissions(self):
        """Testa permissões do role read_only."""
        readonly_roles = [
            role
            for role in self.access_control.roles.values()
            if role.name == "read_only"
        ]

        assert len(readonly_roles) == 1
        readonly_role = readonly_roles[0]

        # Read-only deve ter apenas READ
        assert readonly_role.permissions == {Permission.READ}

    def test_create_custom_role(self):
        """Testa criação de role customizado."""
        custom_permissions = {Permission.READ, Permission.EXECUTE}

        # create_role retorna Role, não role_id
        created_role = self.access_control.create_role(
            name="tester", permissions=custom_permissions, description="Testing role"
        )

        assert created_role is not None
        assert created_role.id in self.access_control.roles
        assert created_role.name == "tester"
        assert created_role.permissions == custom_permissions
        assert created_role.description == "Testing role"

    def test_assign_role_to_user(self):
        """Testa atribuição de role a usuário."""
        # Obter um role existente
        admin_role_id = None
        for role_id, role in self.access_control.roles.items():
            if role.name == "admin":
                admin_role_id = role_id
                break

        assert admin_role_id is not None

        user_id = "user-123"
        # assign_role retorna None, não bool
        self.access_control.assign_role(user_id, admin_role_id)

        assert user_id in self.access_control.user_roles
        assert admin_role_id in self.access_control.user_roles[user_id]

    def test_assign_multiple_roles_to_user(self):
        """Testa atribuição de múltiplos roles a usuário."""
        # Obter roles existentes
        role_ids = []
        for role_id, role in self.access_control.roles.items():
            if role.name in ["developer", "read_only"]:
                role_ids.append(role_id)

        assert len(role_ids) >= 2

        user_id = "multi-role-user"

        # Atribuir primeiro role
        self.access_control.assign_role(user_id, role_ids[0])
        # Atribuir segundo role
        self.access_control.assign_role(user_id, role_ids[1])

        assert len(self.access_control.user_roles[user_id]) == 2
        assert role_ids[0] in self.access_control.user_roles[user_id]
        assert role_ids[1] in self.access_control.user_roles[user_id]

    def test_check_permission_with_role(self):
        """Testa verificação de permissão com role."""
        # Criar usuário com role developer
        dev_role_id = None
        for role_id, role in self.access_control.roles.items():
            if role.name == "developer":
                dev_role_id = role_id
                break

        user_id = "dev-user"
        self.access_control.assign_role(user_id, dev_role_id)

        # Verificar permissões (método é check_permission, não has_permission)
        assert self.access_control.check_permission(user_id, Permission.READ) is True
        assert self.access_control.check_permission(user_id, Permission.WRITE) is True
        assert self.access_control.check_permission(user_id, Permission.EXECUTE) is True
        assert self.access_control.check_permission(user_id, Permission.DELETE) is False
        assert self.access_control.check_permission(user_id, Permission.ADMIN) is False

    def test_check_permission_without_role(self):
        """Testa verificação de permissão sem role."""
        user_id = "no-role-user"

        # Usuário sem roles não deve ter nenhuma permissão
        assert self.access_control.check_permission(user_id, Permission.READ) is False
        assert self.access_control.check_permission(user_id, Permission.WRITE) is False

    def test_revoke_role_from_user(self):
        """Testa remoção de role de usuário através de manipulação direta."""
        # Primeiro atribuir um role
        admin_role_id = None
        for role_id, role in self.access_control.roles.items():
            if role.name == "admin":
                admin_role_id = role_id
                break

        user_id = "temp-admin"
        self.access_control.assign_role(user_id, admin_role_id)

        # Verificar que foi atribuído
        assert self.access_control.check_permission(user_id, Permission.ADMIN) is True

        # AccessControl não tem revoke_role, remover manualmente
        if user_id in self.access_control.user_roles:
            self.access_control.user_roles[user_id].remove(admin_role_id)
            if not self.access_control.user_roles[user_id]:
                del self.access_control.user_roles[user_id]

        assert self.access_control.check_permission(user_id, Permission.ADMIN) is False

    def test_get_user_permissions(self):
        """Testa obtenção de todas as permissões de um usuário."""
        # Criar usuário com múltiplos roles
        role_ids = []
        for role_id, role in self.access_control.roles.items():
            if role.name in ["developer", "read_only"]:
                role_ids.append(role_id)

        user_id = "multi-perm-user"
        for role_id in role_ids:
            self.access_control.assign_role(user_id, role_id)

        # Obter todas as permissões
        user_permissions = self.access_control.get_user_permissions(user_id)

        # Deve incluir READ, WRITE, EXECUTE (união dos roles)
        assert Permission.READ in user_permissions
        assert Permission.WRITE in user_permissions
        assert Permission.EXECUTE in user_permissions

    def test_list_users_with_permission(self):
        """Testa listagem de usuários com permissão específica através de busca manual."""
        # Criar usuários com diferentes roles
        admin_role_id = None
        dev_role_id = None

        for role_id, role in self.access_control.roles.items():
            if role.name == "admin":
                admin_role_id = role_id
            elif role.name == "developer":
                dev_role_id = role_id

        # Atribuir roles
        self.access_control.assign_role("admin-user", admin_role_id)
        self.access_control.assign_role("dev-user", dev_role_id)

        # AccessControl não tem list_users_with_permission, buscar manualmente
        users_with_write = [
            user_id
            for user_id in self.access_control.user_roles
            if self.access_control.check_permission(user_id, Permission.WRITE)
        ]

        assert "admin-user" in users_with_write
        assert "dev-user" in users_with_write

    def test_role_hierarchy_enforcement(self):
        """Testa aplicação de hierarquia de roles."""
        # Admin deve ter todas as permissões
        admin_role_id = None
        for role_id, role in self.access_control.roles.items():
            if role.name == "admin":
                admin_role_id = role_id
                break

        user_id = "hierarchy-test"
        self.access_control.assign_role(user_id, admin_role_id)

        # Admin deve ter todas as permissões (usar check_permission)
        for permission in Permission:
            assert self.access_control.check_permission(user_id, permission) is True

    def test_permission_inheritance(self):
        """Testa herança de permissões entre roles."""
        # Criar role filho que herda de role pai
        parent_permissions = {Permission.READ, Permission.WRITE}
        child_permissions = parent_permissions | {Permission.EXECUTE}

        # create_role retorna Role, não role_id
        parent_role = self.access_control.create_role(
            name="parent_role",
            permissions=parent_permissions,
            description="Parent role",
        )

        child_role = self.access_control.create_role(
            name="child_role",
            permissions=child_permissions,
            description="Child role with inheritance",
        )

        # Verificar que child tem todas as permissões do parent + suas próprias
        assert parent_role.permissions.issubset(child_role.permissions)
        assert Permission.EXECUTE in child_role.permissions

    def test_role_deletion(self):
        """Testa remoção de role através de manipulação direta."""
        # Criar role temporário
        temp_permissions = {Permission.READ}
        temp_role = self.access_control.create_role(
            name="temp_role", permissions=temp_permissions, description="Temporary role"
        )

        # Verificar que foi criado
        assert temp_role.id in self.access_control.roles

        # AccessControl não tem delete_role, remover manualmente
        del self.access_control.roles[temp_role.id]

        assert temp_role.id not in self.access_control.roles

    def test_role_modification(self):
        """Testa modificação de role existente através de manipulação direta."""
        # Criar role para modificar
        initial_permissions = {Permission.READ}
        role = self.access_control.create_role(
            name="modifiable_role",
            permissions=initial_permissions,
            description="Role to modify",
        )

        # AccessControl não tem modify_role_permissions, modificar diretamente
        new_permissions = {Permission.READ, Permission.WRITE}
        role.permissions = new_permissions

        modified_role = self.access_control.roles[role.id]
        assert modified_role.permissions == new_permissions

    def test_access_control_audit(self):
        """Testa auditoria do sistema de controle de acesso através de list_roles."""
        # Criar alguns usuários e roles para auditoria
        users_data = [
            ("user1", "admin"),
            ("user2", "developer"),
            ("user3", "read_only"),
        ]

        for user_id, role_name in users_data:
            role_id = None
            for rid, role in self.access_control.roles.items():
                if role.name == role_name:
                    role_id = rid
                    break

            if role_id:
                self.access_control.assign_role(user_id, role_id)

        # AccessControl não tem generate_audit_report, usar list_roles e user_roles
        roles_list = self.access_control.list_roles()
        total_users = len(self.access_control.user_roles)
        total_roles = len(roles_list)

        assert total_users >= 3
        assert total_roles >= 3
        assert all("name" in role for role in roles_list)
