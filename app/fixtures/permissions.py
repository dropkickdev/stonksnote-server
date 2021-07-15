

crud =  ['create', 'read', 'update', 'delete']
full =  [
    'create', 'read', 'update', 'delete', 'hard_delete',
    'attach', 'detach', 'activate', 'deactivate',
    'moderate',     # This means updating another user's data
]
banning = ['ban', 'unban']

# Add as necessary
# All permissions to choose from. Add to this with each new perm group you create.
# Permissions will create entries for these then just choose which goes to which group.
permission_set = {
    # 108 + 6 (banning)
    'full': [
        'staff', 'admin', 'settings',
        'profile', 'account', 'message',
        'mark', 'collection', 'trade',
        'owner', 'equity', 'broker',
        'user', 'group', 'permission',
        'option', 'token', 'taxonomy',
        'note', 'media', 'upload',
        'visitor',      # Not sure what this is for
        'content', 'foo',
    ],
    'banning': ['user', 'staff', 'admin']     # ban, unban
}


# Groups
# Add as necessary
group_set = ['AccountGroup', 'ContentGroup', 'StaffGroup', 'AdminGroup', 'NoaddGroup']
AccountGroup = {
    'profile': ['read', 'update'],
    'account': ['read', 'update'],
    'upload': crud,
    'message': crud,
}
ContentGroup = {
    'mark': crud,
    'collection': crud,
    'trade': crud,
    'owner': ['read'],
    'equity': ['read'],
    'broker': ['read', 'attach', 'detach'],
    
    # Delete this soon so update wherever this was used
    'content': crud
}

# For attachment
StaffGroup = {
    'user': [*full, *banning],
    'group': full,
    'permission': full,
    'taxonomy': full,
    'owner': full,
    'equity': full,
    'broker': full,
}
AdminGroup = {
    'staff': [*full, *banning],
    'admin': ['read', 'update', *banning],
    'settings': full
}
NoaddGroup = {
    'foo': ['read', 'update', 'delete', 'hard_delete'],
    'user': ['create', 'delete', 'hard_delete'],
}