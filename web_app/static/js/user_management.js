document.addEventListener('DOMContentLoaded', function() {
    initializeUserManagement();
});

function initializeUserManagement() {
    // Role change handler
    const roleSelects = document.querySelectorAll('.role-select');
    roleSelects.forEach(select => {
        select.addEventListener('change', handleRoleChange);
    });

    // User deactivation handler
    document.querySelectorAll('.deactivate-user').forEach(button => {
        button.addEventListener('click', async function() {
            const userId = this.dataset.userId;
            const username = this.dataset.username;
            
            if (confirm(`Are you sure you want to deactivate user "${username}"?`)) {
                try {
                    const response = await fetch('/users/deactivate', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ user_id: userId })
                    });

                    if (response.ok) {
                        showAlert('User deactivated successfully', 'success');
                        this.closest('tr').remove();
                    } else {
                        throw new Error('Failed to deactivate user');
                    }
                } catch (error) {
                    console.error('Error:', error);
                    showAlert('Error deactivating user', 'danger');
                }
            }
        });
    });
}

async function handleRoleChange(event) {
    const userId = event.target.dataset.userId;
    const newRole = event.target.value;
    const originalRole = event.target.getAttribute('data-original-role');

    try {
        const response = await fetch('/users/update_role', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: userId,
                role: newRole
            })
        });

        if (response.ok) {
            showAlert('Role updated successfully', 'success');
            event.target.setAttribute('data-original-role', newRole);
        } else {
            throw new Error('Failed to update role');
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('Error updating role', 'danger');
        // Revert to original role
        event.target.value = originalRole;
    }
}

function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.querySelector('.container').prepend(alertDiv);
    
    setTimeout(() => alertDiv.remove(), 3000);
}