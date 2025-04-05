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
            // Botões de ativar/desativar número
            if (e.target.closest('.toggle-number-status')) {
                const button = e.target.closest('.toggle-number-status');
                const numberId = button.dataset.id;
                const action = button.dataset.action;
                
                let confirmMessage, apiUrl, method;
                
                if (action === 'deactivate') {
                    confirmMessage = 'Tem certeza que deseja desativar este número?';
                    apiUrl = `${getBaseUrl()}/api/numbers/${numberId}`;
                    method = 'DELETE';
                } else if (action === 'reactivate') {
                    confirmMessage = 'Tem certeza que deseja reativar este número?';
                    apiUrl = `${getBaseUrl()}/api/numbers/${numberId}/reactivate`;
                    method = 'POST';
                }
                
                if (confirm(confirmMessage)) {
                    // Enviar solicitação para ativar/desativar número
                    fetch(apiUrl, {
                        method: method,
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            // Mostrar mensagem de sucesso
                            showToast(data.message);
                            
                            // Recarregar a página para atualizar a lista
                            window.location.reload();
                        } else {
                            showToast(data.error || 'Ocorreu um erro', 'danger');
                        }
                    })
                    .catch(error => {
                        console.error('Erro:', error);
                        showToast('Ocorreu um erro ao processar sua solicitação', 'danger');
                    });
                }
            }
            
            // Antigo botão de excluir número - agora escondido
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
                                emptyRow.innerHTML = '<td colspan="5" class="text-center">Nenhum número cadastrado</td>';
                                numbersList.appendChild(emptyRow);
                            }
                        } else {
                            showToast(data.error || data.message || 'Ocorreu um erro', 'danger');
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
                
                // Função de fallback para copiar texto
                function fallbackCopyTextToClipboard(text) {
                    const textArea = document.createElement("textarea");
                    textArea.value = text;
                    
                    // Torna o textarea invisível
                    textArea.style.position = "fixed";
                    textArea.style.top = "0";
                    textArea.style.left = "0";
                    textArea.style.width = "2em";
                    textArea.style.height = "2em";
                    textArea.style.padding = "0";
                    textArea.style.border = "none";
                    textArea.style.outline = "none";
                    textArea.style.boxShadow = "none";
                    textArea.style.background = "transparent";
                    
                    document.body.appendChild(textArea);
                    textArea.focus();
                    textArea.select();
                    
                    try {
                        const successful = document.execCommand('copy');
                        if (successful) {
                            showToast('Link copiado para a área de transferência!');
                        } else {
                            showToast('Não foi possível copiar o link', 'warning');
                        }
                    } catch (err) {
                        console.error('Erro ao usar execCommand:', err);
                        showToast('Erro ao copiar link', 'danger');
                    }
                    
                    document.body.removeChild(textArea);
                }
                
                // Tentar usar a API moderna primeiro, com fallback se não disponível
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(url)
                        .then(() => {
                            showToast('Link copiado para a área de transferência!');
                        })
                        .catch(err => {
                            console.error('Erro ao copiar com Clipboard API:', err);
                            // Se a API moderna falhar, usar o método de fallback
                            fallbackCopyTextToClipboard(url);
                        });
                } else {
                    // Navegador não suporta Clipboard API
                    console.log('Clipboard API não suportada, usando fallback');
                    fallbackCopyTextToClipboard(url);
                }
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
                    showToast(data.error || data.message || 'Erro ao atualizar o link', 'danger');
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                showToast(error.message || 'Ocorreu um erro ao atualizar o link', 'danger');
            });
        });
    }

    // Verificar se estamos na página do dashboard
    if (document.getElementById('dashboard-container')) {
        console.log('Inicializando dashboard...');
        // Definir data inicial como hoje por padrão
        const today = getTodayDate();
        if (document.getElementById('startDate')) {
            document.getElementById('startDate').value = today;
        }
        if (document.getElementById('endDate')) {
            document.getElementById('endDate').value = today;
        }
        
        // Carregar estatísticas iniciais
        updateDashboardAll();
        
        // Adicionar event listeners para os filtros
        document.getElementById('filterButton')?.addEventListener('click', updateDashboardAll);
    }
});

// Função para atualizar as estatísticas do dashboard
function updateDashboardStats() {
    // Obter parâmetros de filtro atuais
    const startDate = document.getElementById('startDate')?.value || getTodayDate();
    const endDate = document.getElementById('endDate')?.value || getTodayDate();
    const linkId = document.getElementById('linkSelector')?.value || 'all';
    
    // Construir URL com os parâmetros de filtro
    let url = `${getBaseUrl()}/api/stats/summary`;
    // Sempre incluir datas
    url += `?start_date=${startDate}&end_date=${endDate}`;
    if (linkId && linkId !== 'all') {
        url += `&link_id=${linkId}`;
    }
    
    // Fazer a requisição para obter as estatísticas
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error('Erro ao obter estatísticas');
            }
            return response.json();
        })
        .then(data => {
            console.log('Estatísticas recebidas:', data);
            // Atualizar os valores nos cards
            if (document.getElementById('totalClicks')) {
                document.getElementById('totalClicks').textContent = data.total_clicks;
            }
            if (document.getElementById('dailyAverage')) {
                document.getElementById('dailyAverage').textContent = data.daily_average;
            }
            if (document.getElementById('activeLinks')) {
                document.getElementById('activeLinks').textContent = data.active_links;
            }
            if (document.getElementById('activeNumbers')) {
                document.getElementById('activeNumbers').textContent = data.active_numbers;
            }
        })
        .catch(error => {
            console.error('Erro ao atualizar estatísticas:', error);
        });
}

// Função para obter a data atual no formato YYYY-MM-DD
function getTodayDate() {
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// Função para atualizar tabela de redirecionamentos recentes
function updateRecentRedirects() {
    // Obter parâmetros de filtro atuais
    const startDate = document.getElementById('startDate')?.value || getTodayDate();
    const endDate = document.getElementById('endDate')?.value || getTodayDate();
    const linkId = document.getElementById('linkSelector')?.value || 'all';
    
    // Construir URL com os parâmetros de filtro
    let url = `${getBaseUrl()}/api/redirects/recent`;
    url += `?start_date=${startDate}&end_date=${endDate}`;
    if (linkId && linkId !== 'all') {
        url += `&link_id=${linkId}`;
    }
    url += '&limit=10&page=1';
    
    // Fazer a requisição para obter os redirecionamentos recentes
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error('Erro ao obter redirecionamentos recentes');
            }
            return response.json();
        })
        .then(data => {
            console.log('Redirecionamentos recentes:', data);
            
            // Verificar se existe a tabela de redirecionamentos
            const recentRedirectsTable = document.getElementById('recentRedirectsTable');
            if (!recentRedirectsTable) return;
            
            const tbody = recentRedirectsTable.querySelector('tbody');
            if (!tbody) return;
            
            // Limpar a tabela
            tbody.innerHTML = '';
            
            // Se não houver redirecionamentos
            if (!data.redirects || data.redirects.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center">Nenhum redirecionamento encontrado</td></tr>';
                return;
            }
            
            // Adicionar os redirecionamentos à tabela
            data.redirects.forEach(redirect => {
                const row = document.createElement('tr');
                
                row.innerHTML = `
                    <td>${redirect.time}</td>
                    <td>${redirect.link_name}</td>
                    <td>${redirect.phone_number}</td>
                    <td>${redirect.ip_address}</td>
                    <td>
                        ${redirect.location.city ? redirect.location.city : ''} 
                        ${redirect.location.region ? redirect.location.region : ''} 
                        ${redirect.location.country ? redirect.location.country : 'Desconhecido'}
                    </td>
                `;
                
                tbody.appendChild(row);
            });
        })
        .catch(error => {
            console.error('Erro ao atualizar redirecionamentos recentes:', error);
        });
}

// Função para atualizar o dashboard completo
function updateDashboardAll() {
    updateDashboardStats();
    updateRecentRedirects();
    updateNumberStats();
}

// Função para atualizar estatísticas por número
function updateNumberStats() {
    // Obter parâmetros de filtro atuais
    const startDate = document.getElementById('startDate')?.value || getTodayDate();
    const endDate = document.getElementById('endDate')?.value || getTodayDate();
    const linkId = document.getElementById('linkSelector')?.value || 'all';
    
    // Construir URL com os parâmetros de filtro
    let url = `${getBaseUrl()}/api/stats/by-number`;
    url += `?start_date=${startDate}&end_date=${endDate}`;
    if (linkId && linkId !== 'all') {
        url += `&link_id=${linkId}`;
    }
    
    // Fazer a requisição para obter as estatísticas por número
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error('Erro ao obter estatísticas por número');
            }
            return response.json();
        })
        .then(data => {
            console.log('Estatísticas por número:', data);
            
            // Verificar se existe a tabela de estatísticas por número
            const numberStats = document.getElementById('numberStats');
            if (!numberStats) {
                console.error("Elemento com id 'numberStats' não encontrado");
                return;
            }
            
            // Limpar a tabela
            numberStats.innerHTML = '';
            
            // Se não houver estatísticas
            if (!data.number_stats || data.number_stats.length === 0) {
                numberStats.innerHTML = '<tr><td colspan="5" class="text-center">Nenhuma estatística encontrada</td></tr>';
                return;
            }
            
            // Adicionar as estatísticas à tabela
            data.number_stats.forEach(stat => {
                const row = document.createElement('tr');
                
                // Calcular a porcentagem para a barra de progresso
                const percentage = stat.percentage;
                
                row.innerHTML = `
                    <td>${stat.phone_number}</td>
                    <td>${stat.description || ''}</td>
                    <td>${stat.access_count}</td>
                    <td>
                        <div class="progress">
                            <div class="progress-bar" role="progressbar" style="width: ${percentage}%"
                                aria-valuenow="${percentage}" aria-valuemin="0" aria-valuemax="100">
                                ${percentage}%
                            </div>
                        </div>
                    </td>
                    <td>${stat.last_access || 'N/A'}</td>
                `;
                
                numberStats.appendChild(row);
            });
        })
        .catch(error => {
            console.error('Erro ao atualizar estatísticas por número:', error);
        });
}

// Verificar se a página atual é dashboard
function isDashboardPage() {
    return !!document.getElementById('dashboard-container');
}

// Loop para atualizar as estatísticas a cada 5 minutos automaticamente
setInterval(function() {
    if (isDashboardPage()) {
        console.log('Atualizando estatísticas automaticamente...');
        updateDashboardAll();
    }
}, 300000); // 5 minutos em milissegundos
