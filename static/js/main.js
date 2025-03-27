// Código de proteção contra interferência de extensões
// Este código protege contra o erro "Cannot read properties of undefined (reading 'toLowerCase')"
// que ocorre devido a alguma extensão do Chrome, possivelmente a extensão pdbbgdjfhcnlemnihdbcolnoocfdekje
(function protectFromExtensions() {
    try {
        // Proteção para toString e toLowerCase em valores indefinidos/nulos
        const originalToString = Object.prototype.toString;
        const originalToLowerCase = String.prototype.toLowerCase;
        
        // Proteção para toString
        Object.prototype.toString = function() {
            if (this === undefined || this === null) {
                console.warn('Tentativa de chamar toString em valor undefined/null');
                return '';
            }
            return originalToString.call(this);
        };
        
        // Proteção para toLowerCase
        String.prototype.toLowerCase = function() {
            if (this === undefined || this === null) {
                console.warn('Tentativa de chamar toLowerCase em valor undefined/null');
                return '';
            }
            return originalToLowerCase.call(this);
        };
        
        console.log('Proteções contra interferência de extensões aplicadas');
    } catch(e) {
        console.error('Erro ao aplicar proteções:', e);
    }
})();

// Função para exibir notificações
function showToast(message, type = 'success') {
    // Criar elemento toast
    const toastDiv = document.createElement('div');
    toastDiv.className = `toast align-items-center text-white bg-${type} border-0`;
    toastDiv.setAttribute('role', 'alert');
    toastDiv.setAttribute('aria-live', 'assertive');
    toastDiv.setAttribute('aria-atomic', 'true');
    
    const toastContent = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Fechar"></button>
        </div>
    `;
    
    toastDiv.innerHTML = toastContent;
    document.body.appendChild(toastDiv);
    
    // Inicializar e mostrar o toast
    const toast = new bootstrap.Toast(toastDiv, {
        autohide: true,
        delay: 3000
    });
    toast.show();
    
    // Remover após ocultar
    toastDiv.addEventListener('hidden.bs.toast', () => {
        document.body.removeChild(toastDiv);
    });
}

// Obter URL base do servidor
function getBaseUrl() {
    return window.location.protocol + '//' + window.location.host;
}

// DOM carregado
document.addEventListener('DOMContentLoaded', function() {
    // Elementos relacionados aos números
    const saveNumberBtn = document.getElementById('saveNumber');
    const numbersList = document.getElementById('numbersList');
    
    // Elementos relacionados aos links
    const saveLinkBtn = document.getElementById('saveLink');
    const updateLinkBtn = document.getElementById('updateLink');
    const linksList = document.getElementById('linksList');
    const linkNameInput = document.getElementById('linkName');
    const previewLink = document.getElementById('previewLink');
    const editLinkNameInput = document.getElementById('editLinkName');
    const editPreviewLink = document.getElementById('editPreviewLink');
    
    // Função para atualizar a visualização prévia do link
    function updateLinkPreview() {
        const baseUrl = getBaseUrl() + '/';
        const linkName = this.value || 'seu-link';
        if (this.id === 'linkName') {
            previewLink.textContent = baseUrl + linkName;
        } else {
            editPreviewLink.textContent = baseUrl + linkName;
        }
    }
    
    // Adicionar listener para visualização prévia do link
    if (linkNameInput) {
        linkNameInput.addEventListener('input', updateLinkPreview);
    }
    
    if (editLinkNameInput) {
        editLinkNameInput.addEventListener('input', updateLinkPreview);
    }

    // Adicionar novo número
    if (saveNumberBtn) {
        saveNumberBtn.addEventListener('click', function() {
            const phoneNumber = document.getElementById('phoneNumber').value.trim();
            const description = document.getElementById('description').value.trim();
            
            if (!phoneNumber) {
                showToast('Por favor, digite um número de telefone válido', 'danger');
                return;
            }
            
            // Validação básica do formato de telefone (apenas números)
            if (!/^\d+$/.test(phoneNumber)) {
                showToast('O número deve conter apenas dígitos, sem espaços ou caracteres especiais', 'danger');
                return;
            }
            
            // Enviar solicitação para adicionar número
            fetch(getBaseUrl() + '/api/numbers', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    phone_number: phoneNumber,
                    description: description
                }),
            })
            .then(response => {
                // Verificar se a resposta foi bem-sucedida
                if (!response.ok) {
                    return response.json().then(errorData => {
                        throw new Error(errorData.error || 'Erro ao adicionar número');
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // Fechar modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('addNumberModal'));
                    modal.hide();
                    
                    // Limpar formulário
                    document.getElementById('phoneNumber').value = '';
                    document.getElementById('description').value = '';
                    
                    // Mostrar mensagem de sucesso
                    showToast(data.message);
                    
                    // Recarregar a página para atualizar a lista
                    window.location.reload();
                } else {
                    showToast(data.error || data.message || 'Erro ao adicionar número', 'danger');
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                showToast(error.message || 'Ocorreu um erro ao adicionar o número', 'danger');
            });
        });
    }
    
    // Excluir número
    if (numbersList) {
        numbersList.addEventListener('click', function(e) {
            if (e.target.closest('.delete-number')) {
                const button = e.target.closest('.delete-number');
                const numberId = button.dataset.id;
                
                if (confirm('Tem certeza que deseja excluir este número?')) {
                    // Enviar solicitação para excluir número
                    fetch(`${getBaseUrl()}/api/numbers/${numberId}`, {
                        method: 'DELETE',
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            // Remover linha da tabela
                            const row = button.closest('tr');
                            row.remove();
                            
                            // Mostrar mensagem de sucesso
                            showToast(data.message);
                            
                            // Se não houver mais números, adicionar mensagem
                            if (numbersList.querySelectorAll('tr').length === 0) {
                                const emptyRow = document.createElement('tr');
                                emptyRow.innerHTML = '<td colspan="4" class="text-center">Nenhum número cadastrado</td>';
                                numbersList.appendChild(emptyRow);
                            }
                        } else {
                            showToast(data.message, 'danger');
                        }
                    })
                    .catch(error => {
                        console.error('Erro:', error);
                        showToast('Ocorreu um erro ao excluir o número', 'danger');
                    });
                }
            }
        });
    }
    
    // Adicionar novo link
    if (saveLinkBtn) {
        saveLinkBtn.addEventListener('click', function() {
            const linkName = document.getElementById('linkName').value.trim();
            const customMessage = document.getElementById('customMessage').value.trim();
            
            if (!linkName) {
                showToast('Por favor, digite um nome para o link', 'danger');
                return;
            }
            
            // Validação do formato do link (apenas letras, números e hífens)
            if (!/^[a-zA-Z0-9-]+$/.test(linkName)) {
                showToast('O nome do link deve conter apenas letras, números e hífens', 'danger');
                return;
            }
            
            // Enviar solicitação para adicionar link
            fetch(getBaseUrl() + '/api/links', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    link_name: linkName,
                    custom_message: customMessage
                }),
            })
            .then(response => {
                // Verificar se a resposta foi bem-sucedida
                if (!response.ok) {
                    return response.json().then(errorData => {
                        throw new Error(errorData.error || 'Erro ao adicionar link');
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // Fechar modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('addLinkModal'));
                    modal.hide();
                    
                    // Limpar formulário
                    document.getElementById('linkName').value = '';
                    document.getElementById('customMessage').value = 'Você será redirecionado para um de nossos atendentes. Aguarde um momento...';
                    
                    // Mostrar mensagem de sucesso
                    showToast(data.message);
                    
                    // Recarregar a página para atualizar a lista
                    window.location.reload();
                } else {
                    showToast(data.error || 'Erro ao adicionar link', 'danger');
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                showToast(error.message || 'Ocorreu um erro ao adicionar o link', 'danger');
            });
        });
    }
    
    // Editar link (abrir modal com dados)
    if (linksList) {
        linksList.addEventListener('click', function(e) {
            // Editar link
            if (e.target.closest('.edit-link')) {
                const button = e.target.closest('.edit-link');
                const linkId = button.dataset.id;
                const linkName = button.dataset.name;
                const customMessage = button.dataset.message;
                
                // Preencher formulário
                document.getElementById('editLinkId').value = linkId;
                document.getElementById('editLinkName').value = linkName;
                document.getElementById('editCustomMessage').value = customMessage;
                
                // Atualizar visualização prévia
                const baseUrl = getBaseUrl() + '/';
                document.getElementById('editPreviewLink').textContent = baseUrl + linkName;
                
                // Abrir modal
                const editLinkModal = new bootstrap.Modal(document.getElementById('editLinkModal'));
                editLinkModal.show();
            }
            
            // Copiar link
            if (e.target.closest('.copy-link')) {
                const button = e.target.closest('.copy-link');
                const url = button.dataset.url;
                
                navigator.clipboard.writeText(url)
                    .then(() => {
                        showToast('Link copiado para a área de transferência!');
                    })
                    .catch(err => {
                        console.error('Erro ao copiar:', err);
                        showToast('Erro ao copiar link', 'danger');
                    });
            }
            
            // Excluir link
            if (e.target.closest('.delete-link')) {
                const button = e.target.closest('.delete-link');
                const linkId = button.dataset.id;
                
                if (confirm('Tem certeza que deseja excluir este link?')) {
                    // Enviar solicitação para excluir link
                    fetch(`${getBaseUrl()}/api/links/${linkId}`, {
                        method: 'DELETE',
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            // Remover linha da tabela
                            const row = button.closest('tr');
                            row.remove();
                            
                            // Mostrar mensagem de sucesso
                            showToast(data.message);
                            
                            // Se não houver mais links, adicionar mensagem
                            if (linksList.querySelectorAll('tr').length === 0) {
                                const emptyRow = document.createElement('tr');
                                emptyRow.innerHTML = '<td colspan="5" class="text-center">Nenhum link personalizado</td>';
                                linksList.appendChild(emptyRow);
                            }
                        } else {
                            showToast(data.message, 'danger');
                        }
                    })
                    .catch(error => {
                        console.error('Erro:', error);
                        showToast('Ocorreu um erro ao excluir o link', 'danger');
                    });
                }
            }
        });
    }
    
    // Atualizar link
    if (updateLinkBtn) {
        updateLinkBtn.addEventListener('click', function() {
            const linkId = document.getElementById('editLinkId').value;
            const linkName = document.getElementById('editLinkName').value.trim();
            const customMessage = document.getElementById('editCustomMessage').value.trim();
            
            if (!linkName) {
                showToast('Por favor, digite um nome para o link', 'danger');
                return;
            }
            
            // Validação do formato do link (apenas letras, números e hífens)
            if (!/^[a-zA-Z0-9-]+$/.test(linkName)) {
                showToast('O nome do link deve conter apenas letras, números e hífens', 'danger');
                return;
            }
            
            // Enviar solicitação para atualizar link
            fetch(`${getBaseUrl()}/api/links/${linkId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    link_name: linkName,
                    custom_message: customMessage
                }),
            })
            .then(response => {
                // Verificar se a resposta foi bem-sucedida
                if (!response.ok) {
                    return response.json().then(errorData => {
                        throw new Error(errorData.error || 'Erro ao atualizar link');
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // Fechar modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('editLinkModal'));
                    modal.hide();
                    
                    // Mostrar mensagem de sucesso
                    showToast(data.message);
                    
                    // Recarregar a página para atualizar a lista
                    window.location.reload();
                } else {
                    showToast(data.error || data.message || 'Erro ao atualizar o link', 'danger');
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                showToast(error.message || 'Ocorreu um erro ao atualizar o link', 'danger');
            });
        });
    }
});
