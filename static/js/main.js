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

// Função para obter URL base
function getBaseUrl() {
    return window.location.protocol + '//' + window.location.host;
}

// Função para detectar se é uma URL válida
function isValidUrl(string) {
    try {
        new URL(string);
        return true;
    } catch (_) {
        return false;
    }
}

// Função para validar o nome do link
function isValidLinkName(linkName) {
    if (!linkName) return false;
    
    console.log("Validando link: " + linkName);
    
    // Verificar caracteres permitidos (letras, números, hífen e barra)
    if (/[^a-zA-Z0-9\-\/]/.test(linkName)) {
        console.log("Link contém caracteres inválidos");
        return false;
    }
    
    // Verificar se tem mais de uma barra
    const segments = linkName.split('/');
    if (segments.length > 2) {
        console.log("Link contém mais de uma barra");
        return false;
    }
    
    // Verificar se algum segmento está vazio
    if (segments.some(s => s === '')) {
        console.log("Link contém segmento vazio");
        return false;
    }
    
    // Verificar palavras reservadas
    const reservedRoutes = ['api', 'login', 'logout', 'admin', 'dashboard', 'administracao', 'static', 'redirect'];
    if (segments.some(s => reservedRoutes.includes(s))) {
        console.log("Link contém palavra reservada");
        return false;
    }
    
    console.log("Link válido!");
    return true;
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
    const editLinkNameInput = document.getElementById('editLinkName');
    
    // Atualizar preview apenas para o modal de edição
    if (editLinkNameInput) {
        editLinkNameInput.addEventListener('input', function() {
            const baseUrl = getBaseUrl() + '/';
            const linkName = this.value || 'seu-link';
            const editPreviewLink = document.getElementById('editPreviewLink');
            if (editPreviewLink) {
                editPreviewLink.textContent = baseUrl + linkName;
            }
        });
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
            .then(response => response.json())
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
                    showToast(data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                showToast('Ocorreu um erro ao adicionar o número', 'danger');
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
            
            // Validação do formato do link usando a função isValidLinkName
            if (!isValidLinkName(linkName)) {
                showToast('Nome de link inválido. Use apenas letras, números, hífens e no máximo uma barra. Evite palavras reservadas.', 'danger');
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
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Fechar modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('addLinkModal'));
                    modal.hide();
                    
                    // Limpar formulário
                    document.getElementById('linkName').value = '';
                    document.getElementById('customMessage').value = '';
                    
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
                showToast('Ocorreu um erro ao adicionar o link', 'danger');
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
            
            // Validação do formato do link usando a função isValidLinkName
            if (!isValidLinkName(linkName)) {
                showToast('Nome de link inválido. Use apenas letras, números, hífens e no máximo uma barra. Evite palavras reservadas.', 'danger');
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
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Fechar modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('editLinkModal'));
                    modal.hide();
                    
                    // Mostrar mensagem de sucesso
                    showToast(data.message || 'Link atualizado com sucesso');
                    
                    // Recarregar a página para atualizar a lista
                    window.location.reload();
                } else {
                    showToast(data.error || 'Erro ao atualizar link', 'danger');
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                showToast('Ocorreu um erro ao atualizar o link', 'danger');
            });
        });
    }
});
