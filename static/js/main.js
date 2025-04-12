/**
 * SiliconFlow 图生视频应用的主JavaScript文件
 */

document.addEventListener('DOMContentLoaded', function() {
    // 初始化工具提示
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // API Key 处理
    const apiKeyInput = document.getElementById('apiKey');
    const apiKeyStatus = document.getElementById('apiKeyStatus');
    const testApiKeyBtn = document.getElementById('testApiKeyBtn');

    if (apiKeyInput) {
        // 从本地存储加载 API Key
        const savedApiKey = localStorage.getItem('siliconflow_api_key');
        if (savedApiKey) {
            apiKeyInput.value = savedApiKey;
        }

        // 当 API Key 变化时保存到本地存储
        apiKeyInput.addEventListener('change', function() {
            if (this.value.trim()) {
                localStorage.setItem('siliconflow_api_key', this.value.trim());
                console.log('API Key 已保存到本地存储');
                // 清除状态信息
                if (apiKeyStatus) {
                    apiKeyStatus.textContent = '';
                    apiKeyStatus.className = 'form-text mt-1';
                }
            } else {
                localStorage.removeItem('siliconflow_api_key');
                console.log('API Key 已从本地存储中移除');
                // 清除状态信息
                if (apiKeyStatus) {
                    apiKeyStatus.textContent = '';
                    apiKeyStatus.className = 'form-text mt-1';
                }
            }
        });
    }

    // API Key 测试功能
    if (testApiKeyBtn && apiKeyInput) {
        testApiKeyBtn.addEventListener('click', async function() {
            const apiKey = apiKeyInput.value.trim();

            if (!apiKey) {
                if (apiKeyStatus) {
                    apiKeyStatus.textContent = '请先输入API Key';
                    apiKeyStatus.className = 'form-text mt-1 text-danger';
                }
                return;
            }

            // 显示测试中状态
            testApiKeyBtn.disabled = true;
            testApiKeyBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 测试中...';
            if (apiKeyStatus) {
                apiKeyStatus.textContent = '正在测试API Key...';
                apiKeyStatus.className = 'form-text mt-1 text-info';
            }

            try {
                const response = await fetch('/api/test_api_key', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ api_key: apiKey })
                });

                const result = await response.json();

                if (result.success) {
                    // API Key 有效
                    if (apiKeyStatus) {
                        apiKeyStatus.textContent = '✅ ' + result.message;
                        apiKeyStatus.className = 'form-text mt-1 text-success';
                    }
                    // 保存有效的 API Key
                    localStorage.setItem('siliconflow_api_key', apiKey);
                } else {
                    // API Key 无效
                    if (apiKeyStatus) {
                        apiKeyStatus.textContent = '❌ ' + result.message;
                        apiKeyStatus.className = 'form-text mt-1 text-danger';
                    }
                }
            } catch (error) {
                console.error('Error testing API Key:', error);
                if (apiKeyStatus) {
                    apiKeyStatus.textContent = '测试API Key时出错，请重试';
                    apiKeyStatus.className = 'form-text mt-1 text-danger';
                }
            } finally {
                // 恢复按钮状态
                testApiKeyBtn.disabled = false;
                testApiKeyBtn.innerHTML = '<i class="bi bi-check-circle"></i> 测试';
            }
        });
    }

    // 随机种子按钮
    const randomSeedBtn = document.getElementById('randomSeedBtn');
    if (randomSeedBtn) {
        randomSeedBtn.addEventListener('click', function() {
            const seedInput = document.getElementById('seed');
            seedInput.value = Math.floor(Math.random() * 2147483647);
        });
    }

    // 多图片预览功能
    const imagesInput = document.getElementById('images');
    const imagePreviewContainer = document.getElementById('imagePreviewContainer');
    const selectedImagesCount = document.getElementById('selectedImagesCount');
    const taskCountInput = document.getElementById('taskCount');
    const totalTaskCount = document.getElementById('totalTaskCount');
    const submitBtnCount = document.getElementById('submitBtnCount');

    // 更新总任务数
    function updateTotalTaskCount() {
        if (imagesInput && imagesInput.files && taskCountInput) {
            const imageCount = imagesInput.files.length;
            const taskCount = parseInt(taskCountInput.value) || 1;
            const total = imageCount * taskCount;

            if (totalTaskCount) {
                totalTaskCount.textContent = total;
            }

            if (submitBtnCount) {
                submitBtnCount.textContent = total;
            }

            return total;
        }
        return 0;
    }

    // 监听任务数量变化
    if (taskCountInput) {
        taskCountInput.addEventListener('input', updateTotalTaskCount);
    }

    if (imagesInput) {
        imagesInput.addEventListener('change', function() {
            // 清空预览容器
            if (imagePreviewContainer) {
                imagePreviewContainer.innerHTML = '';
            }

            // 更新选择的图片数量
            if (selectedImagesCount) {
                selectedImagesCount.textContent = this.files.length;
            }

            // 更新总任务数
            updateTotalTaskCount();

            // 创建预览
            if (this.files && this.files.length > 0) {
                Array.from(this.files).forEach((file, index) => {
                    const reader = new FileReader();

                    reader.onload = function(e) {
                        // 创建预览元素
                        const previewCol = document.createElement('div');
                        previewCol.className = 'col-4 col-md-3 col-lg-2';

                        const previewCard = document.createElement('div');
                        previewCard.className = 'card h-100';

                        const previewImg = document.createElement('img');
                        previewImg.src = e.target.result;
                        previewImg.className = 'card-img-top preview-thumbnail';
                        previewImg.alt = `图片 ${index + 1}`;

                        const previewBody = document.createElement('div');
                        previewBody.className = 'card-body p-2';

                        const previewTitle = document.createElement('p');
                        previewTitle.className = 'card-text small text-center mb-0';
                        previewTitle.textContent = file.name.length > 15 ? file.name.substring(0, 12) + '...' : file.name;

                        previewBody.appendChild(previewTitle);
                        previewCard.appendChild(previewImg);
                        previewCard.appendChild(previewBody);
                        previewCol.appendChild(previewCard);

                        if (imagePreviewContainer) {
                            imagePreviewContainer.appendChild(previewCol);
                        }
                    };

                    reader.readAsDataURL(file);
                });
            }
        });
    }

    // 表单提交处理
    const videoForm = document.getElementById('videoForm');
    const submitBtn = document.getElementById('submitBtn');

    // 在表单提交前确保 API Key 已保存
    if (videoForm && apiKeyInput) {
        videoForm.addEventListener('submit', function(e) {
            // 如果输入了 API Key，确保它被保存
            if (apiKeyInput.value.trim()) {
                localStorage.setItem('siliconflow_api_key', apiKeyInput.value.trim());
            }
        });
    }
    const batchProcessingModal = new bootstrap.Modal(document.getElementById('batchProcessingModal'));
    const taskCreatedModal = new bootstrap.Modal(document.getElementById('taskCreatedModal'));
    const createdTaskCount = document.getElementById('createdTaskCount');
    const batchProgressBar = document.getElementById('batchProgressBar');
    const completedTasksCount = document.getElementById('completedTasksCount');
    const totalTasksCount = document.getElementById('totalTasksCount');

    // 创建单个任务
    async function createTask(formData) {
        try {
            const response = await fetch('/api/tasks', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('网络响应异常');
            }

            return await response.json();
        } catch (error) {
            console.error('Error:', error);
            throw error;
        }
    }

    // 批量创建任务
    async function createBatchTasks(files, taskCount) {
        const totalTasks = files.length * taskCount;
        let completedTasks = 0;
        let successTasks = 0;

        console.log(`创建批量任务: 总共 ${totalTasks} 个任务`);

        // 更新进度条初始值
        if (batchProgressBar) {
            batchProgressBar.style.width = '0%';
            batchProgressBar.textContent = '0%';
            batchProgressBar.setAttribute('aria-valuenow', 0);
        }

        if (totalTasksCount) {
            totalTasksCount.textContent = totalTasks;
        }

        if (completedTasksCount) {
            completedTasksCount.textContent = 0;
        }

        // 显示批处理模态框
        batchProcessingModal.show();

        // 获取表单数据（除了图片外的所有字段）
        const baseFormData = new FormData(videoForm);
        baseFormData.delete('image'); // 删除原始的图片数组

        // 存储所有其他字段的键值对
        const formDataEntries = {};
        for (let [key, value] of baseFormData.entries()) {
            formDataEntries[key] = value;
            console.log(`表单字段: ${key} = ${value}`);
        }

        // 生成批处理ID
        const batchId = 'batch_' + Date.now();

        // 对每个图片创建指定数量的任务
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            console.log(`处理图片 ${i+1}/${files.length}: ${file.name}`);

            for (let j = 0; j < taskCount; j++) {
                try {
                    // 创建新的FormData对象
                    const taskFormData = new FormData();

                    // 添加所有其他字段
                    for (let key in formDataEntries) {
                        taskFormData.append(key, formDataEntries[key]);
                    }

                    // 添加批处理信息
                    taskFormData.append('batch_id', batchId);
                    taskFormData.append('batch_size', totalTasks);
                    taskFormData.append('batch_index', i * taskCount + j);

                    // 添加当前图片
                    taskFormData.append('image', file); // 注意这里使用'image'而不是'images'，因为后端期望的是'image'
                    console.log(`添加图片到任务 ${i+1}.${j+1}: ${file.name}`);

                    // 如果有多个任务，为每个任务生成不同的随机种子
                    if (taskCount > 1 && !taskFormData.get('seed')) {
                        const randomSeed = Math.floor(Math.random() * 2147483647);
                        taskFormData.set('seed', randomSeed);
                        console.log(`为任务 ${i+1}.${j+1} 设置随机种子: ${randomSeed}`);
                    }

                    // 创建任务
                    console.log(`提交任务 ${i+1}.${j+1}...`);
                    const result = await createTask(taskFormData);
                    console.log(`任务 ${i+1}.${j+1} 创建成功: ID=${result.task_id}`);
                    successTasks++;

                } catch (error) {
                    console.error(`创建任务失败 (图片 ${i+1}, 尝试 ${j+1}):`, error);
                }

                // 更新进度
                completedTasks++;
                const progress = Math.round((completedTasks / totalTasks) * 100);
                console.log(`进度: ${completedTasks}/${totalTasks} (${progress}%)`);

                if (batchProgressBar) {
                    batchProgressBar.style.width = `${progress}%`;
                    batchProgressBar.textContent = `${progress}%`;
                    batchProgressBar.setAttribute('aria-valuenow', progress);
                }

                if (completedTasksCount) {
                    completedTasksCount.textContent = completedTasks;
                }
            }
        }

        // 关闭批处理模态框
        batchProcessingModal.hide();

        // 显示成功模态框
        if (createdTaskCount) {
            createdTaskCount.textContent = successTasks;
        }

        taskCreatedModal.show();

        // 重置表单
        videoForm.reset();
        if (imagePreviewContainer) {
            imagePreviewContainer.innerHTML = '';
        }
        if (selectedImagesCount) {
            selectedImagesCount.textContent = '0';
        }
        if (totalTaskCount) {
            totalTaskCount.textContent = '0';
        }
        if (submitBtnCount) {
            submitBtnCount.textContent = '1';
        }

        // 重新加载最近任务
        loadRecentTasks();

        return successTasks;
    }

    if (videoForm) {
        videoForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            // 禁用提交按钮
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 处理中...';
            }

            try {
                const files = imagesInput.files;
                const taskCount = parseInt(taskCountInput.value) || 1;

                if (files.length === 0) {
                    alert('请选择至少一张图片');
                    return;
                }

                console.log(`开始创建任务: ${files.length} 张图片, 每张 ${taskCount} 次`);

                // 批量创建任务
                await createBatchTasks(files, taskCount);

            } catch (error) {
                console.error('Error:', error);
                alert('创建任务时出错。请重试。');
            } finally {
                // 重新启用提交按钮
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="bi bi-play-fill"></i> 生成视频 <span id="submitBtnCount" class="badge bg-light text-primary ms-1">1</span>';
                }
            }
        });
    }

    // Load recent tasks
    loadRecentTasks();

    // 加载最近任务的函数
    function loadRecentTasks() {
        const recentTasksContainer = document.getElementById('recentTasks');

        if (recentTasksContainer) {
            fetch('/api/tasks')
            .then(response => {
                if (!response.ok) {
                    throw new Error('网络响应异常');
                }
                return response.json();
            })
            .then(tasks => {
                if (tasks.length === 0) {
                    recentTasksContainer.innerHTML = '<p class="text-center text-muted">暂无生成记录</p>';
                    return;
                }

                // 只显示最新的5个任务
                const recentTasks = tasks.slice(0, 5);

                let html = '<div class="list-group list-group-flush">';

                recentTasks.forEach(task => {
                    const statusClass = getStatusClass(task.status);
                    const statusText = getStatusText(task.status);
                    const date = new Date(task.created_at);
                    const formattedDate = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`;

                    // 创建一个可点击的卡片，使用图片作为封面
                    const previewUrl = task.status === 'completed' || task.status === 'completed_with_warning' ? `/preview/${task.id}` : '#';
                    const isClickable = task.status === 'completed' || task.status === 'completed_with_warning';

                    // 使用新的CSS类
                    html += `
                        <div class="list-group-item px-0 py-2 border-bottom">
                            <div class="d-flex align-items-center">
                                <a href="${previewUrl}" class="${!isClickable ? 'pe-none' : ''}" style="text-decoration: none;">
                                    <div class="task-cover me-3">
                                        ${task.image_path ?
                                            `<img src="/uploads/${task.image_path}" alt="任务图片">` :
                                            `<div class="w-100 h-100 bg-light d-flex align-items-center justify-content-center"><i class="bi bi-image text-muted"></i></div>`
                                        }
                                        <div class="task-status-badge">
                                            <span class="badge ${statusClass}">${statusText}</span>
                                        </div>
                                    </div>
                                </a>
                                <div class="flex-grow-1">
                                    <div class="d-flex justify-content-between align-items-center">
                                        <div class="task-date">${formattedDate}</div>
                                        <a href="${previewUrl}" class="btn btn-sm ${isClickable ? 'btn-primary' : 'btn-secondary disabled'}">
                                            ${isClickable ? '查看' : '处理中'}
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                });

                html += '</div>';
                recentTasksContainer.innerHTML = html;
            })
            .catch(error => {
                console.error('Error:', error);
                recentTasksContainer.innerHTML = '<p class="text-center text-danger">加载任务失败</p>';
            });
        }
    }

    // 获取状态类的辅助函数
    function getStatusClass(status) {
        switch (status) {
            case 'completed':
                return 'bg-success';
            case 'failed':
                return 'bg-danger';
            case 'completed_with_warning':
                return 'bg-warning';
            case 'pending':
                return 'bg-secondary';
            case 'processing_image':
            case 'refining_prompt':
            case 'generating_video':
            case 'waiting_for_video':
            case 'extending_video':
                return 'bg-info';
            default:
                return 'bg-info';
        }
    }

    // 获取状态文本的辅助函数
    function getStatusText(status) {
        switch (status) {
            case 'completed':
                return '已完成';
            case 'failed':
                return '失败';
            case 'completed_with_warning':
                return '完成但有警告';
            case 'pending':
                return '等待中';
            case 'processing_image':
                return '处理图片中';
            case 'refining_prompt':
                return '精化提示词中';
            case 'generating_video':
                return '生成视频中';
            case 'waiting_for_video':
                return '等待视频生成';
            case 'extending_video':
                return '延长视频中';
            default:
                return status;
        }
    }

    // 格式化日期的辅助函数
    function formatDate(dateString) {
        const date = new Date(dateString);
        return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
    }
});
