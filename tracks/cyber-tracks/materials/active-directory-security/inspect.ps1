# Read-only inventory on YOUR Windows training host. No accounts are created.
whoami /user
whoami /groups
Get-Date -Format o
Get-NetIPConfiguration
# A domain controller with the AD module is required for these:
# Get-ADDomain
# Get-ADGroupMember -Identity LabReaders -Recursive
# (Get-Acl "AD:OU=Training,DC=training,DC=example,DC=test").Access
