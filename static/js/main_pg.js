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

// Função para copiar texto para a área de transferência (fallback)
function copyTextToClipboardFallback(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand('copy');
    document.body.removeChild(textArea);
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
        // Obter ID do usuário da URL do elemento span
        const userId = document.querySelector('.input-group-text').textContent.trim().split('/')[1] || '';
        const baseUrl = getBaseUrl() + '/';
        const linkName = this.value || 'seu-link';
        if (this.id === 'linkName') {
            previewLink.textContent = linkName;
        } else {
            editPreviewLink.textContent = linkName;
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
            
            // Enviar solicitação para adicionar número - USANDO POSTGRESQL
            fetch(getBaseUrl() + '/api/pg/numbers', {
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
                    const modalElement = document.getElementById('addNumberModal');
                    if (modalElement) {
                        const modal = bootstrap.Modal.getInstance(modalElement);
                        if (modal) {
                            modal.hide();
                        }
                    }
                    
                    // Limpar formulário
                    const phoneNumberEl = document.getElementById('phoneNumber');
                    if (phoneNumberEl) {
                        phoneNumberEl.value = '';
                    }
                    
                    const descriptionEl = document.getElementById('description');
                    if (descriptionEl) {
                        descriptionEl.value = '';
                    }
                    
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
                    // Enviar solicitação para excluir número - USANDO POSTGRESQL
                    fetch(`${getBaseUrl()}/api/pg/numbers/${numberId}`, {
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
            
            // Enviar solicitação para adicionar link - USANDO POSTGRESQL
            fetch(getBaseUrl() + '/api/pg/links', {
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
                    const modalElement = document.getElementById('addLinkModal');
                    if (modalElement) {
                        const modal = bootstrap.Modal.getInstance(modalElement);
                        if (modal) {
                            modal.hide();
                        }
                    }
                    
                    // Limpar formulário
                    const linkNameEl = document.getElementById('linkName');
                    if (linkNameEl) {
                        linkNameEl.value = '';
                    }
                    
                    const customMessageEl = document.getElementById('customMessage');
                    if (customMessageEl) {
                        customMessageEl.value = 'Você será redirecionado para um de nossos atendentes. Aguarde um momento...';
                    }
                    
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
                
                // Atualizar visualização prévia - apenas o nome do link
                document.getElementById('editPreviewLink').textContent = linkName;
                
                // Abrir modal
                const editLinkModal = new bootstrap.Modal(document.getElementById('editLinkModal'));
                editLinkModal.show();
            }
            
            // Copiar link
            if (e.target.closest('.copy-link')) {
                const button = e.target.closest('.copy-link');
                const url = button.dataset.url;
                
                // Verificar se a API Clipboard está disponível
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(url)
                        .then(() => {
                            showToast('Link copiado para a área de transferência!');
                        })
                        .catch(err => {
                            console.error('Erro ao copiar:', err);
                            // Fallback para método alternativo
                            copyTextToClipboardFallback(url);
                        });
                } else {
                    // Fallback para navegadores que não suportam a API Clipboard
                    copyTextToClipboardFallback(url);
                }
            }
            
            // Excluir link
            if (e.target.closest('.delete-link')) {
                const button = e.target.closest('.delete-link');
                const linkId = button.dataset.id;
                
                if (confirm('Tem certeza que deseja excluir este link?')) {
                    // Enviar solicitação para excluir link - USANDO POSTGRESQL
                    fetch(`${getBaseUrl()}/api/pg/links/${linkId}`, {
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
            
            // Enviar solicitação para atualizar link - USANDO POSTGRESQL
            fetch(`${getBaseUrl()}/api/pg/links/${linkId}`, {
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
                    const modalElement = document.getElementById('editLinkModal');
                    if (modalElement) {
                        const modal = bootstrap.Modal.getInstance(modalElement);
                        if (modal) {
                            modal.hide();
                        }
                    }
                    
                    // Mostrar mensagem de sucesso
                    showToast(data.message);
                    
                    // Recarregar a página para atualizar a lista
                    window.location.reload();
                } else {
                    showToast(data.error || 'Erro ao atualizar link', 'danger');
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                showToast(error.message || 'Ocorreu um erro ao atualizar o link', 'danger');
            });
        });
    }
});
