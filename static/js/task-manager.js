/**
 * SiliconFlow 图生视频应用的任务管理JavaScript文件
 */

document.addEventListener('DOMContentLoaded', function() {
    // Load tasks
    loadTasks();

    // Set up check all videos button
    const checkAllVideosBtn = document.getElementById('checkAllVideosBtn');
    if (checkAllVideosBtn) {
        checkAllVideosBtn.addEventListener('click', function() {
            checkAllVideosBtn.disabled = true;
            checkAllVideosBtn.innerHTML = '<i class="bi bi-camera-video"></i> <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';

            // 显示状态消息
            const statusElement = document.getElementById('statusMessage');
            if (statusElement) {
                statusElement.textContent = '正在检查所有视频状态...';
                statusElement.classList.remove('d-none');
            }

            // 调用检查所有视频的API
            fetch('/api/tasks/check_all_videos')
                .then(response => response.json())
                .then(data => {
                    console.log('检查所有视频结果:', data);

                    // 更新状态消息
                    if (statusElement) {
                        statusElement.textContent = data.message || '检查完成';
                        setTimeout(() => {
                            statusElement.classList.add('d-none');
                        }, 3000);
                    }

                    // 如果有任务更新了，重新加载任务列表
                    if (data.updated_tasks && data.updated_tasks.length > 0) {
                        return fetchAllTasks().then(tasks => {
                            updateTasksList(tasks);
                        });
                    }
                })
                .catch(error => {
                    console.error('检查所有视频时出错:', error);

                    // 更新状态消息
                    if (statusElement) {
                        statusElement.textContent = '检查视频时出错';
                        statusElement.classList.remove('d-none');
                        setTimeout(() => {
                            statusElement.classList.add('d-none');
                        }, 3000);
                    }
                })
                .finally(() => {
                    checkAllVideosBtn.disabled = false;
                    checkAllVideosBtn.innerHTML = '<i class="bi bi-camera-video"></i> 检查所有视频';
                });
        });
    }

    // Set up auto-refresh
    setInterval(() => refreshTasksWithVideoCheck(), 3000); // 每3秒刷新一次

    // Task details modal
    const taskDetailsModal = new bootstrap.Modal(document.getElementById('taskDetailsModal'));
    const previewBtn = document.getElementById('previewBtn');

    // 刷新任务并检查视频的函数
    async function refreshTasksWithVideoCheck() {
        try {
            // 首先加载所有任务
            const tasks = await fetchAllTasks();

            // 调试信息：打印所有任务
            console.log('所有任务:', tasks);

            // 更新任务列表显示
            updateTasksList(tasks);

            // 找出所有未完成但应该有视频的任务
            const tasksToCheck = tasks.filter(task => {
                // 检查所有有request_id但没有video_path的任务
                // 包括pending, processing, generating_video, waiting_for_video状态
                const shouldCheck = task.request_id &&
                       !task.video_path &&
                       task.status !== 'completed' &&
                       task.status !== 'failed';

                // 调试信息：打印每个任务的检查条件
                console.log(`任务 ${task.id} 检查条件:`, {
                    'request_id存在': !!task.request_id,
                    'video_path不存在': !task.video_path,
                    '状态不是completed': task.status !== 'completed',
                    '状态不是failed': task.status !== 'failed',
                    '最终结果': shouldCheck
                });

                return shouldCheck;
            });

            // 如果有需要检查的任务
            if (tasksToCheck.length > 0) {
                console.log(`检查 ${tasksToCheck.length} 个任务的视频状态...`);

                // 显示检查进度
                const statusElement = document.getElementById('statusMessage');
                if (statusElement) {
                    statusElement.textContent = `正在检查 ${tasksToCheck.length} 个任务的视频状态...`;
                    statusElement.classList.remove('d-none');
                }

                // 对每个任务进行检查
                const checkPromises = tasksToCheck.map(async task => {
                    try {
                        console.log(`开始检查任务 ${task.id} 的视频状态...`);

                        // 直接使用直接检查视频状态的方法
                        if (task.request_id) {
                            console.log(`任务 ${task.id} 有request_id，直接检查视频状态`);
                            return await directCheckVideoStatus(task.id, task.request_id);
                        }

                        // 如果没有request_id，尝试使用原来的方法
                        console.log(`任务 ${task.id} 没有request_id，使用原来的方法检查视频状态`);
                        const response = await fetch(`/api/tasks/${task.id}/check_video`);
                        if (!response.ok) {
                            console.log(`任务 ${task.id} 检查失败，状态码: ${response.status}`);
                            return false;
                        }

                        const result = await response.json();
                        console.log(`任务 ${task.id} 视频状态检查结果:`, result);
                        return result.updated;
                    } catch (error) {
                        console.error(`检查任务 ${task.id} 的视频状态时出错:`, error);
                        return false;
                    }
                });

                // 等待所有检查完成
                const results = await Promise.all(checkPromises);
                const updatedCount = results.filter(Boolean).length;

                // 更新状态消息
                if (statusElement) {
                    if (updatedCount > 0) {
                        statusElement.textContent = `已更新 ${updatedCount} 个任务的视频状态`;
                        setTimeout(() => {
                            statusElement.classList.add('d-none');
                        }, 3000);
                    } else {
                        statusElement.classList.add('d-none');
                    }
                }

                // 如果有任务更新了，重新加载任务列表
                if (updatedCount > 0) {
                    console.log(`有 ${updatedCount} 个任务的视频状态已更新，重新加载任务列表...`);
                    const updatedTasks = await fetchAllTasks();
                    updateTasksList(updatedTasks);
                }
            }

            return tasks;
        } catch (error) {
            console.error('刷新任务列表时出错:', error);
            throw error;
        }
    }

    // 直接检查视频状态的函数
    async function directCheckVideoStatus(taskId, requestId) {
        try {
            console.log(`直接检查任务 ${taskId} 的视频状态，request_id: ${requestId}`);

            // 获取保存的 API Key
            const apiKey = localStorage.getItem('siliconflow_api_key') || '';

            // 调用直接检查视频状态的API
            const response = await fetch('/api/check_video_status', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    request_id: requestId,
                    api_key: apiKey
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error(`直接检查视频状态失败:`, errorData);
                return false;
            }

            const result = await response.json();
            console.log(`直接检查视频状态结果:`, result);

            // 如果视频生成成功，更新任务状态
            if (result.status === 'Succeed' && result.results && result.results.videos && result.results.videos.length > 0) {
                const videoUrl = result.results.videos[0].url;

                if (videoUrl) {
                    // 更新任务状态
                    const updateResponse = await fetch(`/api/tasks/${taskId}/update_video`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            video_url: videoUrl
                        })
                    });

                    if (updateResponse.ok) {
                        console.log(`任务 ${taskId} 的视频状态已更新`);
                        return true;
                    }
                }
            }

            return false;
        } catch (error) {
            console.error(`直接检查视频状态时出错:`, error);
            return false;
        }
    }

    // 获取所有任务
    async function fetchAllTasks() {
        const response = await fetch('/api/tasks');
        if (!response.ok) {
            throw new Error('网络响应异常');
        }
        return await response.json();
    }

    // 更新任务列表显示
    function updateTasksList(tasks) {
        const tasksList = document.getElementById('tasksList');

        if (!tasksList) return;

        if (tasks.length === 0) {
            tasksList.innerHTML = '<tr><td colspan="4" class="text-center py-4"><p class="text-muted">暂无任务记录</p></td></tr>';
            return;
        }

        // 构建任务层级结构
        const rootTasks = [];
        const childTasks = {};

        // 先分类任务
        tasks.forEach(task => {
            if (!task.parent_task_id) {
                rootTasks.push(task);
            } else {
                if (!childTasks[task.parent_task_id]) {
                    childTasks[task.parent_task_id] = [];
                }
                childTasks[task.parent_task_id].push(task);
            }
        });

        let html = '';

        // 生成任务行 HTML
        function generateTaskRow(task, isChild = false) {
            const statusClass = getStatusClass(task.status);
            const statusText = getStatusText(task.status);

            return `
                <tr class="task-row ${isChild ? 'child-task' : ''}" data-task-id="${task.id}">
                    <td>
                        ${isChild ? '<div class="ms-4">' : ''}
                        ${task.image_path ?
                            `<img src="/uploads/${task.image_path}" class="task-image-thumbnail" alt="任务图片">` :
                            '无图片'}
                        ${isChild ? '</div>' : ''}
                    </td>
                    <td>
                        ${isChild ? '<div class="ms-4">' : ''}
                        <span class="badge ${statusClass}">${statusText}</span>
                        <small class="d-block mt-1 text-muted text-truncate" style="max-width: 200px;">${task.message || ''}</small>
                        ${isChild ? '</div>' : ''}
                    </td>
                    <td>${formatDate(task.created_at)}</td>
                    <td>
                        <div class="d-flex gap-1 flex-wrap">
                            <button class="btn btn-sm btn-outline-secondary view-details-btn" data-task-id="${task.id}">
                                详情
                            </button>
                            ${task.video_path ?
                                `<a href="/preview/${task.id}" class="btn btn-sm btn-primary">预览</a>` :
                                ''}
                            <button class="btn btn-sm btn-outline-primary regenerate-btn" data-task-id="${task.id}">
                                再次生成
                            </button>
                            ${task.video_path ?
                                `<button class="btn btn-sm btn-outline-info last-frame-btn" data-task-id="${task.id}">
                                    使用最后一帧
                                </button>` :
                                ''}
                            <button class="btn btn-sm btn-outline-danger delete-task-btn" data-task-id="${task.id}">
                                删除
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }

        // 生成根任务及其子任务的HTML
        rootTasks.forEach(task => {
            html += generateTaskRow(task);

            // 添加子任务
            if (childTasks[task.id]) {
                childTasks[task.id].forEach(childTask => {
                    html += generateTaskRow(childTask, true);
                });
            }
        });

        tasksList.innerHTML = html;

        // 为详情按钮添加事件监听器
        document.querySelectorAll('.view-details-btn').forEach(button => {
            button.addEventListener('click', function() {
                const taskId = this.getAttribute('data-task-id');
                showTaskDetails(taskId);
            });
        });

        // 为删除按钮添加事件监听器
        document.querySelectorAll('.delete-task-btn').forEach(button => {
            button.addEventListener('click', function(e) {
                e.stopPropagation(); // 阻止事件冒泡
                const taskId = this.getAttribute('data-task-id');
                deleteTask(taskId);
            });
        });

        // 为再次生成按钮添加事件监听器
        document.querySelectorAll('.regenerate-btn').forEach(button => {
            button.addEventListener('click', function(e) {
                e.stopPropagation(); // 阻止事件冒泡
                const taskId = this.getAttribute('data-task-id');
                regenerateTask(taskId);
            });
        });

        // 为使用最后一帧按钮添加事件监听器
        document.querySelectorAll('.last-frame-btn').forEach(button => {
            button.addEventListener('click', function(e) {
                e.stopPropagation(); // 阻止事件冒泡
                const taskId = this.getAttribute('data-task-id');
                regenerateFromLastFrame(taskId);
            });
        });

        // 为任务行添加事件监听器
        document.querySelectorAll('.task-row').forEach(row => {
            row.addEventListener('click', function(e) {
                // 只在点击不是按钮或链接时触发
                if (!e.target.closest('button') && !e.target.closest('a')) {
                    const taskId = this.getAttribute('data-task-id');
                    showTaskDetails(taskId);
                }
            });
        });
    }

    // 加载任务的函数 (兼容旧代码)
    function loadTasks() {
        refreshTasksWithVideoCheck().catch(error => {
            console.error('Error:', error);
            const tasksList = document.getElementById('tasksList');
            if (tasksList) {
                tasksList.innerHTML = '<tr><td colspan="5" class="text-center py-4"><p class="text-danger">加载任务失败</p></td></tr>';
            }
        });
    }

    // 显示任务详情的函数
    function showTaskDetails(taskId) {
        const taskDetailsBody = document.getElementById('taskDetailsBody');

        // 显示加载动画
        taskDetailsBody.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">加载中...</span>
                </div>
                <p class="mt-2 text-muted">正在加载任务详情...</p>
            </div>
        `;

        // 更新预览按钮
        if (previewBtn) {
            previewBtn.href = `/preview/${taskId}`;
        }

        // 显示模态框
        taskDetailsModal.show();

        // 获取任务详情
        fetch(`/api/tasks/${taskId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('网络响应异常');
            }
            return response.json();
        })
        .then(task => {
            const statusClass = getStatusClass(task.status);
            const statusText = getStatusText(task.status);
            const modelName = task.model || 'Wan2.1-I2V-14B-720P';
            const shortModelName = modelName.split('/').pop();

            let html = `
                <div class="row">
                    <div class="col-md-6">
                        <h6 class="mb-3">任务信息</h6>
                        <div class="mb-2">
                            <span class="text-muted">状态：</span>
                            <span class="badge ${statusClass}">${statusText}</span>
                        </div>
                        <div class="mb-2">
                            <span class="text-muted">消息：</span> ${task.message || '无'}
                        </div>
                        <div class="mb-2">
                            <span class="text-muted">创建时间：</span> ${formatDate(task.created_at)}
                        </div>
                        <div class="mb-2">
                            <span class="text-muted">更新时间：</span> ${formatDate(task.updated_at)}
                        </div>
                        ${task.parent_task_id ?
                            `<div class="mb-2">
                                <span class="text-muted">父任务：</span>
                                <button class="btn btn-sm btn-link p-0 view-details-btn" data-task-id="${task.parent_task_id}">查看原始任务</button>
                            </div>` :
                            ''}
                    </div>
                    <div class="col-md-6">
                        ${task.image_path ?
                            `<h6 class="mb-3">原始图片</h6>
                            <div class="text-center">
                                <img src="/uploads/${task.image_path}" class="img-fluid rounded" alt="原始图片" style="max-height: 200px;">
                            </div>` :
                            ''}
                    </div>
                </div>
            `;

            if (task.prompt) {
                html += `
                    <div class="row mt-3">
                        <div class="col-12">
                            <h6 class="mb-2">生成的提示词</h6>
                            <div class="card bg-light">
                                <div class="card-body py-2 px-3">
                                    <p class="small mb-0">${task.prompt}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }

            if (task.video_path) {
                html += `
                    <div class="row mt-3">
                        <div class="col-12">
                            <h6 class="mb-2">生成的视频</h6>
                            <div class="ratio ratio-16x9 video-player-container">
                                <video controls>
                                    <source src="/output/${task.video_path}" type="video/mp4">
                                    您的浏览器不支持视频标签。
                                </video>
                            </div>
                            <div class="d-flex justify-content-between align-items-center mt-2">
                                <span class="text-muted small">生成于 ${formatDate(task.updated_at)}</span>
                                <a href="/output/${task.video_path}" download class="btn btn-sm btn-primary">
                                    <i class="bi bi-download"></i> 下载视频
                                </a>
                            </div>
                        </div>
                    </div>
                `;

                // 启用预览按钮
                if (previewBtn) {
                    previewBtn.classList.remove('disabled');
                }
            } else {
                // 禁用预览按钮
                if (previewBtn) {
                    previewBtn.classList.add('disabled');
                }
            }

            taskDetailsBody.innerHTML = html;
        })
        .catch(error => {
            console.error('Error:', error);
            taskDetailsBody.innerHTML = '<p class="text-center text-danger">加载任务详情失败</p>';
        });
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
        return moment(dateString).format('YYYY-MM-DD HH:mm:ss');
    }

    // 删除任务的函数
    async function deleteTask(taskId) {
        if (!confirm('确定要删除此任务吗？这将同时删除相关的图片和视频文件，且无法恢复。')) {
            return;
        }

        try {
            const response = await fetch(`/api/tasks/${taskId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || '删除任务失败');
            }

            const result = await response.json();

            // 显示成功消息
            const statusElement = document.getElementById('statusMessage');
            if (statusElement) {
                statusElement.textContent = result.message || '任务已成功删除';
                statusElement.classList.remove('d-none');
                setTimeout(() => {
                    statusElement.classList.add('d-none');
                }, 3000);
            }

            // 刷新任务列表
            refreshTasksWithVideoCheck();

        } catch (error) {
            console.error('删除任务时出错:', error);
            alert(`删除任务时出错: ${error.message}`);
        }
    }

    // 再次生成任务的函数
    async function regenerateTask(taskId) {
        try {
            // 显示加载中的提示
            const statusElement = document.getElementById('statusMessage');
            if (statusElement) {
                statusElement.textContent = '正在准备再次生成...';
                statusElement.classList.remove('d-none');
            }

            // 获取保存的 API Key
            const apiKey = localStorage.getItem('siliconflow_api_key') || '';

            // 调用再次生成API
            const response = await fetch(`/api/tasks/${taskId}/regenerate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    api_key: apiKey
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || '再次生成失败');
            }

            const result = await response.json();

            // 显示成功消息
            if (statusElement) {
                statusElement.textContent = result.message || '任务已成功提交再次生成';
                setTimeout(() => {
                    statusElement.classList.add('d-none');
                }, 3000);
            }

            // 刷新任务列表
            refreshTasksWithVideoCheck();

        } catch (error) {
            console.error('再次生成任务时出错:', error);
            alert(`再次生成失败: ${error.message}`);

            // 隐藏状态消息
            const statusElement = document.getElementById('statusMessage');
            if (statusElement) {
                statusElement.classList.add('d-none');
            }
        }
    }

    // 使用最后一帧再次生成的函数
    async function regenerateFromLastFrame(taskId) {
        try {
            // 显示加载中的提示
            const statusElement = document.getElementById('statusMessage');
            if (statusElement) {
                statusElement.textContent = '正在提取视频最后一帧并准备生成...';
                statusElement.classList.remove('d-none');
            }

            // 获取保存的 API Key
            const apiKey = localStorage.getItem('siliconflow_api_key') || '';

            // 调用使用最后一帧再次生成API
            const response = await fetch(`/api/tasks/${taskId}/regenerate_from_last_frame`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    api_key: apiKey
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || '使用最后一帧再次生成失败');
            }

            const result = await response.json();

            // 显示成功消息
            if (statusElement) {
                statusElement.textContent = result.message || '任务已成功提交，使用最后一帧再次生成';
                setTimeout(() => {
                    statusElement.classList.add('d-none');
                }, 3000);
            }

            // 刷新任务列表
            refreshTasksWithVideoCheck();

        } catch (error) {
            console.error('使用最后一帧再次生成时出错:', error);
            alert(`使用最后一帧再次生成失败: ${error.message}`);

            // 隐藏状态消息
            const statusElement = document.getElementById('statusMessage');
            if (statusElement) {
                statusElement.classList.add('d-none');
            }
        }
    }
});
