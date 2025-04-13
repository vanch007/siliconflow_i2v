/**
 * SiliconFlow 图生视频应用的任务管理JavaScript文件
 */

document.addEventListener('DOMContentLoaded', function() {
    // Load tasks
    loadTasks();

    // 选中的视频任务ID
    let selectedVideoTasks = [];

    // 合并视频按钮
    const mergeVideosBtn = document.getElementById('mergeVideosBtn');

    // 检查ffmpeg是否可用
    checkFFmpegAvailability();

    // 全选复选框
    const selectAllVideos = document.getElementById('selectAllVideos');
    if (selectAllVideos) {
        selectAllVideos.addEventListener('change', function() {
            const checkboxes = document.querySelectorAll('.video-select-checkbox');
            checkboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
                // 触发change事件以更新选中状态
                const event = new Event('change');
                checkbox.dispatchEvent(event);
            });
        });
    }

    // 合并视频按钮点击事件
    if (mergeVideosBtn) {
        mergeVideosBtn.addEventListener('click', function() {
            if (selectedVideoTasks.length < 2) {
                alert('请至少选择两个视频任务进行合并');
                return;
            }

            // 确认合并
            if (!confirm(`确定要合并选中的 ${selectedVideoTasks.length} 个视频吗？`)) {
                return;
            }

            // 禁用按钮并显示加载状态
            mergeVideosBtn.disabled = true;
            mergeVideosBtn.innerHTML = '<i class="bi bi-collection-play"></i> <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';

            // 显示状态消息
            const statusElement = document.getElementById('statusMessage');
            if (statusElement) {
                statusElement.textContent = '正在提交视频合并任务...';
                statusElement.classList.remove('d-none');
            }

            // 获取保存的 API Key
            const apiKey = localStorage.getItem('siliconflow_api_key') || '';

            // 调用合并视频API
            fetch('/api/merge_videos', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    task_ids: selectedVideoTasks,
                    api_key: apiKey
                })
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(errorData => {
                        throw new Error(errorData.error || `服务器错误: ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                console.log('合并视频结果:', data);

                // 更新状态消息
                if (statusElement) {
                    statusElement.textContent = data.message || '视频合并任务已提交';
                    setTimeout(() => {
                        statusElement.classList.add('d-none');
                    }, 3000);
                }

                // 重新加载任务列表
                refreshTasksWithVideoCheck();

                // 清空选中的视频
                selectedVideoTasks = [];
                updateMergeButtonState();

                // 取消全选
                if (selectAllVideos) {
                    selectAllVideos.checked = false;
                }
            })
            .catch(error => {
                console.error('合并视频时出错:', error);

                // 更新状态消息
                if (statusElement) {
                    statusElement.textContent = '合并视频时出错';
                    statusElement.classList.remove('d-none');
                    setTimeout(() => {
                        statusElement.classList.add('d-none');
                    }, 3000);
                }

                // 检查是否是ffmpeg不可用的错误
                if (error.message && error.message.includes('ffmpeg')) {
                    alert('无法合并视频: ' + error.message + '\n\n请安装ffmpeg后再尝试。');
                } else {
                    alert('合并视频时出错: ' + error.message);
                }
            })
            .finally(() => {
                // 恢复按钮状态
                mergeVideosBtn.disabled = (selectedVideoTasks.length < 2);
                mergeVideosBtn.innerHTML = '<i class="bi bi-collection-play"></i> 合并选中视频';
            });
        });
    }

    // 更新合并按钮状态的函数
    function updateMergeButtonState() {
        if (mergeVideosBtn) {
            mergeVideosBtn.disabled = (selectedVideoTasks.length < 2);
        }
    }

    // 处理视频选择变化的函数
    function handleVideoSelectionChange(taskId, checked) {
        console.log(`视频选择变化: taskId=${taskId}, checked=${checked}`);
        console.log('选择前的视频列表:', [...selectedVideoTasks]);

        if (checked) {
            // 添加到选中列表（如果不存在）
            if (!selectedVideoTasks.includes(taskId)) {
                selectedVideoTasks.push(taskId);
            }
        } else {
            // 从选中列表中移除
            selectedVideoTasks = selectedVideoTasks.filter(id => id !== taskId);
        }

        console.log('选择后的视频列表:', [...selectedVideoTasks]);

        // 更新合并按钮状态
        updateMergeButtonState();
    }

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
    setInterval(() => refreshTasksWithVideoCheck(), 10000); // 每10秒刷新一次

    // Task details modal
    const taskDetailsModal = new bootstrap.Modal(document.getElementById('taskDetailsModal'));
    const previewBtn = document.getElementById('previewBtn');

    // 刷新任务并检查视频的函数
    async function refreshTasksWithVideoCheck() {
        try {
            // 记录当前选中的视频列表，用于调试
            console.log('刷新前选中的视频列表:', [...selectedVideoTasks]);

            // 显示状态消息
            const statusElement = document.getElementById('statusMessage');
            if (statusElement && !statusElement.textContent) {
                statusElement.textContent = '正在加载任务列表...';
                statusElement.classList.remove('d-none');
            }

            // 首先加载所有任务
            const tasks = await fetchAllTasks();

            // 调试信息：打印所有任务
            console.log('所有任务:', tasks);

            // 更新任务列表显示
            updateTasksList(tasks);

            // 隐藏状态消息
            if (statusElement && statusElement.textContent === '正在加载任务列表...') {
                statusElement.classList.add('d-none');
            }

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
                    '父任务ID': task.parent_task_id || '无',
                    '最终结果': shouldCheck
                });

                return shouldCheck;
            });

            // 打印需要检查的任务数量
            console.log(`需要检查的任务数量: ${tasksToCheck.length}`);
            if (tasksToCheck.length > 0) {
                console.log('需要检查的任务:', tasksToCheck);
            }

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
        try {
            console.log('开始获取任务列表...');

            // 设置请求超时
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10秒超时

            try {
                const response = await fetch('/api/tasks', {
                    signal: controller.signal,
                    cache: 'no-store' // 禁用缓存，确保每次都获取最新数据
                });

                // 清除超时定时器
                clearTimeout(timeoutId);

                if (!response.ok) {
                    let errorMessage = `网络响应异常 (${response.status})`;
                    try {
                        // 尝试解析错误消息
                        const errorData = await response.json();
                        if (errorData && errorData.error) {
                            errorMessage = errorData.error;
                        }
                    } catch (e) {
                        // 如果无法解析JSON，尝试获取文本
                        try {
                            const errorText = await response.text();
                            if (errorText) {
                                errorMessage = errorText;
                            }
                        } catch (textError) {
                            console.error('无法获取错误消息文本:', textError);
                        }
                    }

                    console.error(`获取任务列表失败: HTTP ${response.status}`, errorMessage);
                    throw new Error(errorMessage);
                }

                const data = await response.json();
                console.log(`成功获取任务列表，共 ${data.length} 条任务`);
                return data;
            } catch (fetchError) {
                // 清除超时定时器
                clearTimeout(timeoutId);

                // 如果是超时错误
                if (fetchError.name === 'AbortError') {
                    console.error('获取任务列表超时');
                    throw new Error('获取任务列表超时，请检查网络连接并重试');
                }

                throw fetchError;
            }
        } catch (error) {
            console.error('获取任务列表时出错:', error);
            throw error;
        }
    }

    // 更新任务列表显示
    function updateTasksList(tasks) {
        console.log('更新任务列表前选中的视频:', [...selectedVideoTasks]);
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
            // 调试信息：打印每个任务的ID和父任务ID
            console.log(`任务ID: ${task.id}, 父任务ID: ${task.parent_task_id || '无'}, 状态: ${task.status}`);

            if (!task.parent_task_id) {
                rootTasks.push(task);
            } else {
                if (!childTasks[task.parent_task_id]) {
                    childTasks[task.parent_task_id] = [];
                }
                childTasks[task.parent_task_id].push(task);
            }
        });

        // 调试信息：打印根任务和子任务的数量
        console.log(`根任务数量: ${rootTasks.length}`);
        console.log('子任务映射:', childTasks);

        let html = '';

        // 生成任务行 HTML
        function generateTaskRow(task, isChild = false, level = 1) {
            const statusClass = getStatusClass(task.status);
            const statusText = getStatusText(task.status);
            const hasVideo = task.video_path && task.status === 'completed';
            // 根据层级计算缩进的像素值
            const indentSize = level * 40; // 每一层级增加 40px 缩进，增大缩进距离

            return `
                <tr class="task-row ${isChild ? 'child-task bg-light' : ''}" data-task-id="${task.id}">
                    <td>
                        ${hasVideo ?
                            `<div class="form-check">
                                <input class="form-check-input video-select-checkbox" type="checkbox" value="${task.id}" data-task-id="${task.id}" ${selectedVideoTasks.includes(task.id) ? 'checked' : ''}>
                            </div>` :
                            ''}
                    </td>
                    <td>
                        ${isChild ? `<div style="margin-left: ${indentSize}px;">` : ''}
                        ${task.image_path ?
                            `<img src="/uploads/${task.image_path}" class="task-image-thumbnail" alt="任务图片">` :
                            '无图片'}
                        ${isChild ? '</div>' : ''}
                    </td>
                    <td>
                        ${isChild ? `<div style="margin-left: ${indentSize}px;">` : ''}
                        <span class="badge ${statusClass}">${statusText}</span>
                        <small class="d-block mt-1 text-muted text-truncate" style="max-width: 200px;">${task.message || ''}</small>
                        ${isChild ? '</div>' : ''}
                    </td>
                    <td>${formatDate(task.created_at)}</td>
                    <td>
                        <div class="task-actions">
                            <div class="action-group">
                                <button class="btn btn-outline-secondary view-details-btn" data-task-id="${task.id}">
                                    <i class="bi bi-info-circle-fill"></i> 详情
                                </button>
                                ${task.video_path ?
                                    `<a href="/preview/${task.id}" class="btn btn-primary"><i class="bi bi-play-circle-fill"></i> 预览</a>` :
                                    ''}
                            </div>

                            <div class="action-group">
                                <button class="btn btn-outline-primary regenerate-btn" data-task-id="${task.id}">
                                    <i class="bi bi-arrow-clockwise"></i> 再次生成
                                </button>
                                ${task.video_path ?
                                    `<button class="btn btn-outline-info last-frame-btn" data-task-id="${task.id}">
                                        <i class="bi bi-film"></i> 最后一帧
                                    </button>` :
                                    ''}
                            </div>

                            <div class="action-group">
                                <button class="btn btn-outline-secondary open-folder-btn" data-task-id="${task.id}" data-type="video">
                                    <i class="bi bi-folder2-open"></i> 文件夹
                                </button>
                                <button class="btn btn-outline-danger delete-task-btn" data-task-id="${task.id}">
                                    <i class="bi bi-trash3-fill"></i> 删除
                                </button>
                            </div>
                        </div>
                    </td>
                </tr>
            `;
        }

        // 生成根任务及其子任务的HTML
        rootTasks.forEach(task => {
            html += generateTaskRow(task);

            // 递归添加子任务及其子任务
            function addChildTasks(parentId, level = 1) {
                if (childTasks[parentId]) {
                    childTasks[parentId].forEach(childTask => {
                        html += generateTaskRow(childTask, true, level);
                        // 递归添加子任务的子任务
                        addChildTasks(childTask.id, level + 1);
                    });
                }
            }

            // 开始递归添加子任务
            addChildTasks(task.id);
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

        // 为打开文件夹按钮添加事件监听器
        document.querySelectorAll('.open-folder-btn').forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault(); // 阻止默认行为
                e.stopPropagation(); // 阻止事件冒泡
                const taskId = this.getAttribute('data-task-id');
                const folderType = this.getAttribute('data-type') || 'auto';
                openTaskFolder(taskId, folderType);
            });
        });

        // 为任务行添加事件监听器
        document.querySelectorAll('.task-row').forEach(row => {
            row.addEventListener('click', function(e) {
                // 只在点击不是按钮、链接或复选框时触发
                if (!e.target.closest('button') && !e.target.closest('a') && !e.target.closest('.form-check')) {
                    const taskId = this.getAttribute('data-task-id');
                    showTaskDetails(taskId);
                }
            });
        });

        // 为视频选择复选框添加事件监听器
        document.querySelectorAll('.video-select-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                const taskId = this.getAttribute('data-task-id');
                handleVideoSelectionChange(taskId, this.checked);
            });
        });
    }

    // 加载任务的函数 (兼容旧代码)
    function loadTasks() {
        // 显示加载中的提示
        const tasksList = document.getElementById('tasksList');
        if (tasksList) {
            tasksList.innerHTML = '<tr><td colspan="5" class="text-center py-4"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">加载中...</span></div><p class="mt-2 text-muted">正在加载任务列表...</p></td></tr>';
        }

        // 添加重试逻辑
        let retryCount = 0;
        const maxRetries = 3;

        function attemptLoad() {
            refreshTasksWithVideoCheck().catch(error => {
                console.error('Error loading tasks:', error);
                retryCount++;

                if (retryCount < maxRetries) {
                    console.log(`尝试重新加载任务列表 (第 ${retryCount} 次重试)...`);
                    // 显示重试中的提示
                    if (tasksList) {
                        tasksList.innerHTML = `<tr><td colspan="5" class="text-center py-4"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">重试中...</span></div><p class="mt-2 text-muted">正在重试加载任务列表 (第 ${retryCount} 次重试)...</p></td></tr>`;
                    }

                    // 等待一秒后重试
                    setTimeout(attemptLoad, 1000);
                } else {
                    // 重试次数用完，显示错误消息
                    if (tasksList) {
                        tasksList.innerHTML = '<tr><td colspan="5" class="text-center py-4"><p class="text-danger">加载任务失败</p><button id="retryLoadTasksBtn" class="btn btn-sm btn-outline-primary mt-2">重新加载</button></td></tr>';

                        // 添加重新加载按钮的点击事件
                        const retryBtn = document.getElementById('retryLoadTasksBtn');
                        if (retryBtn) {
                            retryBtn.addEventListener('click', function() {
                                retryCount = 0; // 重置重试计数
                                loadTasks(); // 重新加载任务
                            });
                        }
                    }

                    // 显示错误消息
                    const statusElement = document.getElementById('statusMessage');
                    if (statusElement) {
                        statusElement.textContent = '加载任务失败，请刷新页面或点击重新加载按钮';
                        statusElement.classList.remove('d-none');
                        setTimeout(() => {
                            statusElement.classList.add('d-none');
                        }, 5000);
                    }
                }
            });
        }

        // 开始加载
        attemptLoad();
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
                            </div>
` :
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
                                <div>
                                    <a href="/output/${task.video_path}" download class="btn btn-sm btn-primary me-2">
                                        <i class="bi bi-download"></i> 下载视频
                                    </a>
                                    <button class="btn btn-sm btn-outline-secondary open-folder-btn" data-task-id="${task.id}" data-type="video">
                                        <i class="bi bi-folder2-open"></i> 打开视频文件夹
                                    </button>
                                </div>
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
            case 'merging_videos':
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
            case 'merging_videos':
                return '视频合成中';
            default:
                return status;
        }
    }

    // 格式化日期的辅助函数
    function formatDate(dateString) {
        try {
            // 检查moment是否可用
            if (typeof moment === 'function') {
                return moment(dateString).format('YYYY-MM-DD HH:mm:ss');
            }

            // 如果moment不可用，使用原生方法
            const date = new Date(dateString);
            return date.toLocaleString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            });
        } catch (error) {
            console.error('格式化日期时出错:', error);
            // 返回原始字符串
            return dateString || '';
        }
    }

    // 检查ffmpeg是否可用
    async function checkFFmpegAvailability() {
        try {
            // 获取保存的 API Key
            const apiKey = localStorage.getItem('siliconflow_api_key') || '';

            // 调用合并视频API，但不提交任务，只是检查ffmpeg是否可用
            const response = await fetch('/api/merge_videos', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    task_ids: ['test1', 'test2'],  // 使用虚拟的任务ID
                    api_key: apiKey
                })
            });

            const data = await response.json();
            console.log('检查ffmpeg可用性结果:', data);

            // 如果返回的错误代码是 ffmpeg_not_available，则禁用合并视频按钮
            if (data.code === 'ffmpeg_not_available') {
                const mergeVideosBtn = document.getElementById('mergeVideosBtn');
                if (mergeVideosBtn) {
                    mergeVideosBtn.disabled = true;
                    mergeVideosBtn.title = '需要安装ffmpeg才能使用视频合并功能';
                    mergeVideosBtn.innerHTML = '<i class="bi bi-collection-play"></i> 合并视频 (需要ffmpeg)';

                    // 显示提示消息
                    const statusElement = document.getElementById('statusMessage');
                    if (statusElement) {
                        statusElement.textContent = '视频合并功能已禁用，需要安装ffmpeg';
                        statusElement.classList.remove('d-none');
                        setTimeout(() => {
                            statusElement.classList.add('d-none');
                        }, 5000);
                    }
                }
            } else if (data.success) {
                // ffmpeg可用，确保合并按钮正常工作
                console.log('ffmpeg可用，路径:', data.ffmpeg_path);
                const mergeVideosBtn = document.getElementById('mergeVideosBtn');
                if (mergeVideosBtn) {
                    // 按钮状态将由选中的视频数量决定
                    updateMergeButtonState();
                }
            }
        } catch (error) {
            console.error('检查ffmpeg可用性时出错:', error);
        }
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

    // 打开任务文件夹的函数
    async function openTaskFolder(taskId, folderType = 'auto') {
        try {
            // 显示加载中的提示
            const statusElement = document.getElementById('statusMessage');
            if (statusElement) {
                statusElement.textContent = '正在打开文件夹...';
                statusElement.classList.remove('d-none');
            }

            // 调用打开文件夹API
            const response = await fetch(`/api/tasks/${taskId}/open_folder?type=${folderType}`);

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || '打开文件夹失败');
            }

            const result = await response.json();
            console.log('打开文件夹结果:', result);

            // 显示成功消息
            if (statusElement) {
                statusElement.textContent = result.message || '文件夹已打开';
                setTimeout(() => {
                    statusElement.classList.add('d-none');
                }, 3000);
            }

        } catch (error) {
            console.error('打开文件夹时出错:', error);
            alert(`打开文件夹失败: ${error.message}`);

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
                statusElement.textContent = '正在获取任务信息...';
                statusElement.classList.remove('d-none');
            }

            // 首先获取原任务的提示词
            const taskResponse = await fetch(`/api/tasks/${taskId}`);
            if (!taskResponse.ok) {
                throw new Error('获取任务信息失败');
            }

            const taskData = await taskResponse.json();
            console.log('获取到的任务信息:', taskData);

            // 隐藏状态消息
            if (statusElement) {
                statusElement.classList.add('d-none');
            }

            // 显示风格提示词确认模态框
            const promptModal = new bootstrap.Modal(document.getElementById('promptConfirmModal'));
            const stylePromptTextarea = document.getElementById('stylePrompt');
            const lastFrameTaskIdInput = document.getElementById('lastFrameTaskId');
            const lastFramePreviewImg = document.getElementById('lastFramePreview');
            const lastFrameImagePathInput = document.getElementById('lastFrameImagePath');

            // 设置原始提示词和任务ID
            stylePromptTextarea.value = taskData.prompt || '';
            lastFrameTaskIdInput.value = taskId;

            // 设置图片预览
            if (taskData.video_path) {
                // 如果有视频，则显示视频的最后一帧作为预览
                // 我们使用一个特殊的API端点来获取最后一帧
                lastFramePreviewImg.src = `/api/tasks/${taskId}/last_frame?t=${new Date().getTime()}`;
                lastFramePreviewImg.alt = '视频最后一帧';
                lastFrameImagePathInput.value = `last_frame_${taskId}.jpg`;
            } else if (taskData.image_path) {
                // 如果没有视频但有原始图片，则显示原始图片
                lastFramePreviewImg.src = `/uploads/${taskData.image_path}`;
                lastFramePreviewImg.alt = '原始图片';
                lastFrameImagePathInput.value = taskData.image_path;
            } else {
                // 如果都没有，显示一个占位图片
                lastFramePreviewImg.src = '/static/img/no-image.png';
                lastFramePreviewImg.alt = '无可用图片';
                lastFrameImagePathInput.value = '';
            }

            // 显示模态框
            promptModal.show();

            // 为确认按钮添加事件监听器
            const confirmPromptBtn = document.getElementById('confirmPromptBtn');

            // 移除现有的事件监听器，防止重复添加
            const newConfirmBtn = confirmPromptBtn.cloneNode(true);
            confirmPromptBtn.parentNode.replaceChild(newConfirmBtn, confirmPromptBtn);

            // 添加新的事件监听器
            newConfirmBtn.addEventListener('click', async () => {
                // 关闭模态框
                promptModal.hide();

                // 显示加载中的提示
                if (statusElement) {
                    statusElement.textContent = '正在提取视频最后一帧并准备生成...';
                    statusElement.classList.remove('d-none');
                }

                // 获取保存的 API Key 和用户修改后的提示词
                const apiKey = localStorage.getItem('siliconflow_api_key') || '';
                const userPrompt = document.getElementById('stylePrompt').value;

                // 调用使用最后一帧再次生成API
                try {
                    const response = await fetch(`/api/tasks/${taskId}/regenerate_from_last_frame`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            api_key: apiKey,
                            prompt: userPrompt // 传递用户修改后的提示词
                        })
                    });

                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.error || '使用最后一帧再次生成失败');
                    }

                    const result = await response.json();
                    console.log('使用最后一帧生成的新任务:', result);

                    // 显示成功消息
                    if (statusElement) {
                        statusElement.textContent = result.message || '任务已成功提交，使用最后一帧再次生成';
                        setTimeout(() => {
                            statusElement.classList.add('d-none');
                        }, 3000);
                    }

                    // 立即刷新任务列表，以显示新创建的任务
                    console.log('刷新任务列表以显示新创建的任务...');
                    await refreshTasksWithVideoCheck();

                    // 再次刷新任务列表，确保新任务显示
                    setTimeout(async () => {
                        console.log('再次刷新任务列表...');
                        await refreshTasksWithVideoCheck();
                    }, 1000);

                } catch (error) {
                    console.error('使用最后一帧再次生成时出错:', error);
                    alert(`使用最后一帧再次生成失败: ${error.message}`);

                    // 隐藏状态消息
                    if (statusElement) {
                        statusElement.classList.add('d-none');
                    }
                }
            });

        } catch (error) {
            console.error('准备使用最后一帧再次生成时出错:', error);
            alert(`准备使用最后一帧再次生成失败: ${error.message}`);

            // 隐藏状态消息
            const statusElement = document.getElementById('statusMessage');
            if (statusElement) {
                statusElement.classList.add('d-none');
            }
        }
    }
});
