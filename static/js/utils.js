let CHINESE2ENGLISH = {
    '纯白': 'White',
    '浅灰': 'Gainsboro',
    '亚麻色': 'Linen',
    '柠檬黄': 'LemonChiffon',
    '蜜瓜绿': 'Honeydew',
    '淡绿': 'PaleGreen1',
    '淡蓝': 'LightBlue',
    '橙红': 'Salmon',
    '纯黑': 'Black',
}

let COLORNAME2RGB = {
    'White': 0xFFFFFF,
    'Gainsboro': 0xDCDCDC,
    'Linen': 0xFAF0E6,
    'LemonChiffon': 0xFFFACD,
    'Honeydew': 0xF0FFF0,
    'PaleGreen1': 0x9AFF9A,
    'LightBlue': 0xADD8E6,
    'Salmon': 0xFA8072,
    'Black': 0x000000,
};


function ply_vis(ply_file_path, doc_canvas_id, opts={}) {
    function _get_width () {
        let canvas = $('#' + doc_canvas_id);
        let width = parseInt(canvas.css('width').slice(0, -2));
        
        if (opts['width'] !== undefined) {
            width = opts['width'];
        } else if (opts['width_ratio'] !== undefined) {
            width = window.innerWidth / opts['width_ratio'];
        }
        return width;
    }

    function _get_height () {
        let canvas = $('#' + doc_canvas_id);
        let height = parseInt(canvas.css('height').slice(0, -2));
        
        if (opts['height'] !== undefined) {
            height = opts['height'];
        } else if (opts['height_ratio'] !== undefined) {
            height = window.innerHeight / opts['height_ratio'];
        }
        return height;
    }

    let width = _get_width();
    let height = _get_height();

    rotated = false;
    if (opts['rotated'] !== undefined) {
        rotated = opts['rotated'];
    }

    let point_size = 0.005;
    if (opts['point_size'] !== undefined) { point_size = opts['point_size']; }
    let rotate_speed = 0.01;
    if (opts['rotate_speed'] !== undefined) { rotate_speed = opts['rotate_speed']; }
    let rotate_axis = 'y';
    if (opts['rotate_axis'] !== undefined) { rotate_axis = opts['rotate_axis']; }
    let canvas_color = 0xD0D0D0;
    if (opts['canvas_color'] !== undefined) { canvas_color = COLORNAME2RGB[CHINESE2ENGLISH[opts['canvas_color']]]; }
    let fixed_color = false
    if (opts['fixed_color'] !== undefined) { fixed_color = opts['fixed_color']; }

    let requestAnimationFrame = (function () {
        return window.requestAnimationFrame ||
            window.webkitRequestAnimationFrame ||
            window.mozRequestAnimationFrame ||
            window.oRequestAnimationFrame ||
            window.msRequestAnimationFrame ||
            function (callback) {
                window.setTimeout(callback, 1000 / 60);
            };
    })();

    let info = document.getElementById(doc_canvas_id);
    let scene; //用来盛放模型的场景
    let camera; //呈现模型的相机
    let renderer; //渲染模型的渲染器
    let control; //操作模型的控制器
    let objLoader; //加载obj模型的加载器
    let group = new THREE.Group();
    
    //场景内模型渲染准备
    function prepareRender() {
        scene = new THREE.Scene();
        scene.background = new THREE.Color(canvas_color);
        camera = new THREE.PerspectiveCamera(70, width / height, 1, 10000000000);
        renderer = new THREE.WebGLRenderer();
        renderer.autoClear = false;

        //初始化相机位置。
        camera.position.x = 150;
        camera.position.y = 150;
        camera.position.z = 150;
        renderer.setSize(width, height);

        //将渲染画布放到dom元素中，即前面声明的div。
        info.appendChild(renderer.domElement);

        //声明控制器，传入相机和被控制的dom节点。
        control = new THREE.OrbitControls(camera, renderer.domElement.parentNode);

        //控制器在控制元素时围绕的中心位置。
        control.target = new THREE.Vector3(0, 0, 0);

        //相机的朝向
        camera.aspect = window.innerWidth / window.innerHeight;
    }

    function insertObj_normalize() {
        let loader = new THREE.PLYLoader();
        loader.load(ply_file_path, function (geometry) {
            let scale_ratio = opts['scale_ratio'];


            // 获取顶点位置数组
            let positions = geometry.attributes.position.array;

            // 创建一个新的数组存储转换后的顶点
            let transformedPositions = new Float32Array(positions.length);

            for (let i = 0; i < positions.length; i += 3) {
                let x = positions[i];
                let y = positions[i + 1];
                let z = positions[i + 2];

                // 转换为 zxy
                transformedPositions[i] = x;
                transformedPositions[i + 1] = z;
                transformedPositions[i + 2] = y;
            }

            // 更新几何体的顶点位置
            geometry.setAttribute('position', new THREE.Float32BufferAttribute(transformedPositions, 3));


            // 更新顶点法向量
            geometry.computeVertexNormals();

            // 计算几何体质心
            geometry.computeBoundingBox();
            let boundingBox = geometry.boundingBox;
            let center = new THREE.Vector3();
            boundingBox.getCenter(center);

            // 平移几何体到原点
            geometry.translate(-center.x, -center.y, -center.z);

            // 计算包围盒的最大边长
            let size = new THREE.Vector3();
            boundingBox.getSize(size); // 获取包围盒的尺寸
            let maxLength = Math.max(size.x, size.y, size.z); // 找到最长边

            // 计算缩放比例
            target_length = 2
            let norm_ratio = target_length / maxLength;
            scale_ratio *= norm_ratio

            // 创建材质并添加到场景
            // let material = new THREE.PointsMaterial({ size: point_size });
            // material.vertexColors = true;
            // let mesh = new THREE.Points(geometry, material);

            // 创建一个基本的 Mesh 材质
            let material;
            if (fixed_color) {
                material = new THREE.MeshBasicMaterial({
                    wireframe: true,  // 是否显示线框，设为 true 会显示线框
                    side: THREE.DoubleSide, // 双面渲染（可选）
                    color: 0xFFFFFF,    // 固定颜色
                });
            } else {
                material = new THREE.MeshBasicMaterial({
                    wireframe: true,  // 是否显示线框，设为 true 会显示线框
                    side: THREE.DoubleSide, // 双面渲染（可选）
                    vertexColors: true,  // 顶点颜色
                });
            }

            // 创建一个 Mesh 对象并将几何体和材质传入
            let mesh = new THREE.Mesh(geometry, material);


            // 缩放模型
            mesh.scale.set(scale_ratio, scale_ratio, scale_ratio);

            group.add(mesh);
            scene.add(group);
        },
        function (xhr) {
            // 进度条逻辑
            if (opts['doc_progress_id'] !== undefined && opts['doc_progress_bar_id'] !== undefined) {
                let progress = $('#' + opts['doc_progress_id']);
                let progress_bar = $('#' + opts['doc_progress_bar_id']);

                let progress_val = parseInt(xhr.loaded / xhr.total * 100);
                progress_bar.attr('aria-valuenow', progress_val);
                progress_bar.attr('style', 'width:' + progress_val + '%');
                progress_bar.html('' + progress_val + '%');

                if (progress_val === 100) {
                    progress_bar.addClass('progress-bar-success');
                    progress_bar.html('加载完成');
                    if (opts['progress_hide']) {
                        setTimeout(function () {
                            progress.hide();
                        }, 2000);
                    }
                }
            }
        },
        function (error) {
            console.error('加载 PLY 文件时出错:', error);
        });
    }


    //场景内添加灯
    function insertOther() {
        //环境光
        // let light = new THREE.AmbientLight( 0x404040 ); // soft white light
        let light = new THREE.AmbientLight(0xffffff);
        scene.add(light);

        //方向光
        let directionalLight = new THREE.DirectionalLight(0xffffff, 0.5);
        scene.add(directionalLight);
    }
    
    function render() {
        width = _get_width();
        height = _get_height();
        renderer.setSize(width, height);
        renderer.render(scene, camera);
    }
    
    let animate_id = requestAnimationFrame(animate);
    function animate() {
        if ($('#' + doc_canvas_id).length === 0) { // stop animate
            cancelAnimationFrame(animate_id);
            return;
        }

        if (rotated) { 
            if ('x' === rotate_axis) {
                group.rotation.x -= rotate_speed;
            } else if ('y' === rotate_axis) {
                group.rotation.y -= rotate_speed;
            } else if ('z' === rotate_axis) {
                group.rotation.z -= rotate_speed;
            } else if ('-x' === rotate_axis) {
                group.rotation.x += rotate_speed;
            } else if ('-y' === rotate_axis) {
                group.rotation.y += rotate_speed;
            } else {
                group.rotation.z += rotate_speed;
            }
        }
        control.update();
        requestAnimationFrame(animate);
        render();
    }

    function init() {
        prepareRender();
        insertObj_normalize();
        insertOther();
        animate();
    }

    init();
}

function ply_vis_landmark(landmark_mesh_path, landmark_point_path, doc_canvas_id, opts={}) {
    function _get_width () {
        let canvas = $('#' + doc_canvas_id);
        let width = parseInt(canvas.css('width').slice(0, -2));

        if (opts['width'] !== undefined) {
            width = opts['width'];
        } else if (opts['width_ratio'] !== undefined) {
            width = window.innerWidth / opts['width_ratio'];
        }
        return width;
    }

    function _get_height () {
        let canvas = $('#' + doc_canvas_id);
        let height = parseInt(canvas.css('height').slice(0, -2));

        if (opts['height'] !== undefined) {
            height = opts['height'];
        } else if (opts['height_ratio'] !== undefined) {
            height = window.innerHeight / opts['height_ratio'];
        }
        return height;
    }

    let width = _get_width();
    let height = _get_height();

    rotated = false;
    if (opts['rotated'] !== undefined) {
        rotated = opts['rotated'];
    }

    let point_size = 0.005;
    if (opts['point_size'] !== undefined) { point_size = opts['point_size']; }
    let rotate_speed = 0.01;
    if (opts['rotate_speed'] !== undefined) { rotate_speed = opts['rotate_speed']; }
    let rotate_axis = 'y';
    if (opts['rotate_axis'] !== undefined) { rotate_axis = opts['rotate_axis']; }
    let canvas_color = 0xD0D0D0;
    if (opts['canvas_color'] !== undefined) { canvas_color = COLORNAME2RGB[CHINESE2ENGLISH[opts['canvas_color']]]; }
    let fixed_color = false
    if (opts['fixed_color'] !== undefined) { fixed_color = opts['fixed_color']; }

    let requestAnimationFrame = (function () {
        return window.requestAnimationFrame ||
            window.webkitRequestAnimationFrame ||
            window.mozRequestAnimationFrame ||
            window.oRequestAnimationFrame ||
            window.msRequestAnimationFrame ||
            function (callback) {
                window.setTimeout(callback, 1000 / 60);
            };
    })();

    let info = document.getElementById(doc_canvas_id);
    let scene; //用来盛放模型的场景
    let camera; //呈现模型的相机
    let renderer; //渲染模型的渲染器
    let control; //操作模型的控制器
    let objLoader; //加载obj模型的加载器

    //场景内模型渲染准备
    function prepareRender() {
        scene = new THREE.Scene();
        scene.background = new THREE.Color(canvas_color);
        camera = new THREE.PerspectiveCamera(70, width / height, 1, 10000000000);
        renderer = new THREE.WebGLRenderer();
        renderer.autoClear = false;

        //初始化相机位置。
        camera.position.x = 150;
        camera.position.y = 150;
        camera.position.z = 150;
        renderer.setSize(width, height);

        //将渲染画布放到dom元素中，即前面声明的div。
        info.appendChild(renderer.domElement);

        //声明控制器，传入相机和被控制的dom节点。
        control = new THREE.OrbitControls(camera, renderer.domElement.parentNode);

        //控制器在控制元素时围绕的中心位置。
        control.target = new THREE.Vector3(0, 0, 0);

        //相机的朝向
        camera.aspect = window.innerWidth / window.innerHeight;
    }


    function insertObj_normalize() {
        console.log(landmark_mesh_path);
        console.log(landmark_mesh_path.length);
        console.log(landmark_point_path);
        console.log(landmark_point_path.length);

        let loader = new THREE.PLYLoader();
        let minX = Infinity, minY = Infinity, minZ = Infinity;
        let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity;

        // 加载模型的 Promise 函数
        const loadModel = (path) => {
            return new Promise((resolve, reject) => {
                loader.load(
                    path,
                    (geometry) => {
                        let positions = geometry.attributes.position.array;
                        // 转换为 zxy 格式
                        let transformedPositions = new Float32Array(positions.length);
                        for (let i = 0; i < positions.length; i += 3) {
                            transformedPositions[i] = positions[i];
                            transformedPositions[i + 1] = positions[i + 2]; // z -> y
                            transformedPositions[i + 2] = positions[i + 1]; // y -> z
                        }
                        geometry.setAttribute(
                            'position',
                            new THREE.Float32BufferAttribute(transformedPositions, 3)
                        );
                        geometry.computeVertexNormals();

                        positions = geometry.attributes.position.array;
                        for (let i = 0; i < positions.length; i += 3) {
                            minX = Math.min(minX, positions[i]);
                            maxX = Math.max(maxX, positions[i]);
                            minY = Math.min(minY, positions[i + 1]);
                            maxY = Math.max(maxY, positions[i + 1]);
                            minZ = Math.min(minZ, positions[i + 2]);
                            maxZ = Math.max(maxZ, positions[i + 2]);
                        }
                        resolve(geometry);
                    },
                    undefined,
                    (error) => reject(error)
                );
            });
        };

        // 加载特征点的 Promise 函数
        const loadPoints = (path) => {
            return new Promise((resolve, reject) => {
                loader.load(
                    path,
                    (geometry) => {
                        let positions = geometry.attributes.position.array;

                        // 转换为 zxy 格式
                        let transformedPositions = new Float32Array(positions.length);
                        for (let i = 0; i < positions.length; i += 3) {
                            transformedPositions[i] = positions[i];
                            transformedPositions[i + 1] = positions[i + 2]; // z -> y
                            transformedPositions[i + 2] = positions[i + 1]; // y -> z
                        }
                        geometry.setAttribute(
                            'position',
                            new THREE.Float32BufferAttribute(transformedPositions, 3)
                        );
                        geometry.computeVertexNormals();
                        resolve(geometry);
                    },
                    undefined,
                    (error) => reject(error)
                );
            });
        };

        // 加载所有模型和特征点
        const loadAll = async () => {
            try {
                // 加载所有模型
                const modelGeometries = await Promise.all(
                    landmark_mesh_path.map((path) => loadModel(path))
                );

                // 计算中心点和缩放比例
                console.log("Bounding box:", [minX, maxX, minY, maxY, minZ, maxZ]);

                let center = new THREE.Vector3(
                    (minX + maxX) / 2,
                    (minY + maxY) / 2,
                    (minZ + maxZ) / 2
                );
                let maxLength = Math.max(maxX - minX, maxY - minY, maxZ - minZ);
                let target_length = 2;
                let norm_ratio = target_length / maxLength;
                let scale_ratio = opts["scale_ratio"] * norm_ratio;

                // 将模型添加到场景
                modelGeometries.forEach((geometry, index) => {
                    geometry.translate(-center.x, -center.y, -center.z);
                    geometry.computeVertexNormals();

                    let material = new THREE.MeshBasicMaterial({
                        wireframe: true,
                        side: THREE.DoubleSide,
                        color: fixed_color ? 0xffffff : undefined,
                        vertexColors: !fixed_color,
                    });

                    let mesh = new THREE.Mesh(geometry, material);
                    mesh.scale.set(scale_ratio, scale_ratio, scale_ratio);

                    let group = new THREE.Group();
                    group.add(mesh);
                    scene.add(group);
                    console.log(`Added model: ${landmark_mesh_path[index]}`);
                });

                // 加载所有特征点
                const pointGeometries = await Promise.all(
                    landmark_point_path.map((path) => loadPoints(path))
                );

                // 将特征点添加到场景
                pointGeometries.forEach((geometry, index) => {
                    geometry.translate(-center.x, -center.y, -center.z);
                    geometry.computeVertexNormals();

                    let material = new THREE.PointsMaterial({
                        size: 5,
                        vertexColors: true,
                    });

                    let points = new THREE.Points(geometry, material);
                    points.scale.set(scale_ratio, scale_ratio, scale_ratio);

                    let group = new THREE.Group();
                    group.add(points);
                    scene.add(group);
                    console.log(`Added points: ${landmark_point_path[index]}`);
                });
            } catch (error) {
                console.error("Error loading models or points:", error);
            }
        };

        // 开始加载
        loadAll();
    }



    // 向场景中添加物体
    function insertObj_normalize_ori() {
        console.log(landmark_mesh_path)
        console.log(landmark_mesh_path.length)
        console.log(landmark_point_path)
        console.log(landmark_point_path.length)

        let loader = new THREE.PLYLoader();

        // 找到所有模型的包围盒
        let minX = 10000;
        let minY = 10000;
        let minZ = 10000;
        let maxX = -10000;
        let maxY = -10000;
        let maxZ = -10000;
        for (let j = 0; j < landmark_mesh_path.length; j++) {
            console.log(landmark_mesh_path[j])
            loader.load(landmark_mesh_path[j], function (geometry) {
                // 获取顶点位置数组
                let positions = geometry.attributes.position.array;
                for (let i = 0; i < positions.length; i += 3) {
                    minX = Math.min(minX, positions[i])
                    maxX = Math.max(maxX, positions[i])
                    minY = Math.min(minY, positions[i + 1])
                    maxY = Math.max(maxY, positions[i + 1])
                    minZ = Math.min(minZ, positions[i + 2])
                    maxZ = Math.max(maxZ, positions[i + 2])
                }
            })
        }

        console.log([minX, maxX, minY, maxY, minZ, maxZ])

        minX = -46.73401
        maxX = 43.0852
        minY = -28.521526
        maxY = 37.680084
        minZ = -119.06942
        maxZ = -83.24421

        let center = new THREE.Vector3();
        center.x = (minX + maxX) / 2
        center.y = (minY + maxY) / 2
        center.z = (minZ + maxZ) / 2

        let maxLength = Math.max(maxX - minX, maxY - minY, maxZ - minZ)
        // 计算缩放比例
        let target_length = 2
        let norm_ratio = target_length / maxLength;

        // 缩放
        let scale_ratio = opts['scale_ratio'];
        scale_ratio *= norm_ratio

        // 加载模型
        for (let i = 0; i < landmark_mesh_path.length; i++) {
            loader.load(landmark_mesh_path[i], function (geometry) {
                // 获取顶点位置数组
                let positions = geometry.attributes.position.array;

                // 创建一个新的数组存储转换后的顶点
                let transformedPositions = new Float32Array(positions.length);

                for (let i = 0; i < positions.length; i += 3) {
                    let x = positions[i];
                    let y = positions[i + 1];
                    let z = positions[i + 2];

                    // 转换为 zxy
                    transformedPositions[i] = x;
                    transformedPositions[i + 1] = z;
                    transformedPositions[i + 2] = y;
                }

                // 更新几何体的顶点位置
                geometry.setAttribute('position', new THREE.Float32BufferAttribute(transformedPositions, 3));


                // 更新顶点法向量
                geometry.computeVertexNormals();

                // 平移几何体到原点
                geometry.translate(-center.x, -center.y, -center.z);

                // 创建材质并添加到场景
                // let material = new THREE.PointsMaterial({ size: point_size });
                // material.vertexColors = true;
                // let mesh = new THREE.Points(geometry, material);

                // 创建一个基本的 Mesh 材质
                let material;
                if (fixed_color) {
                    material = new THREE.MeshBasicMaterial({
                        wireframe: true,  // 是否显示线框，设为 true 会显示线框
                        side: THREE.DoubleSide, // 双面渲染（可选）
                        color: 0xFFFFFF,    // 固定颜色
                    });
                } else {
                    material = new THREE.MeshBasicMaterial({
                        wireframe: true,  // 是否显示线框，设为 true 会显示线框
                        side: THREE.DoubleSide, // 双面渲染（可选）
                        vertexColors: true,  // 顶点颜色
                    });
                }

                // 创建一个 Mesh 对象并将几何体和材质传入
                let mesh = new THREE.Mesh(geometry, material);

                // 缩放模型
                mesh.scale.set(scale_ratio, scale_ratio, scale_ratio);

                let group = new THREE.Group();
                group.add(mesh);
                scene.add(group);
                console.log(landmark_mesh_path[i]);
            })
        }

        // 加载特征点
        for (let i = 0; i < landmark_point_path.length; i++) {
            loader.load(landmark_point_path[i], function (geometry) {
                // 获取顶点位置数组
                let positions = geometry.attributes.position.array;

                // 创建一个新的数组存储转换后的顶点
                let transformedPositions = new Float32Array(positions.length);

                for (let i = 0; i < positions.length; i += 3) {
                    let x = positions[i];
                    let y = positions[i + 1];
                    let z = positions[i + 2];

                    // 转换为 zxy
                    transformedPositions[i] = x;
                    transformedPositions[i + 1] = z;
                    transformedPositions[i + 2] = y;
                }

                // 更新几何体的顶点位置
                geometry.setAttribute('position', new THREE.Float32BufferAttribute(transformedPositions, 3));


                // 更新顶点法向量
                geometry.computeVertexNormals();

                // 平移几何体到原点
                geometry.translate(-center.x, -center.y, -center.z);

                // 创建材质并添加到场景
                let material = new THREE.PointsMaterial({ size: point_size });
                material.vertexColors = true;
                let mesh = new THREE.Points(geometry, material);

                // 创建一个 Mesh 对象并将几何体和材质传入
                let point_mesh = new THREE.Mesh(geometry, material);

                // 缩放模型
                point_mesh.scale.set(scale_ratio, scale_ratio, scale_ratio);

                let group = new THREE.Group();
                group.add(point_mesh);
                scene.add(group)
                console.log(landmark_point_path[i]);
            })
        }

    }


    //场景内添加灯
    function insertOther() {
        //环境光
        // let light = new THREE.AmbientLight( 0x404040 ); // soft white light
        let light = new THREE.AmbientLight(0xffffff);
        scene.add(light);

        //方向光
        let directionalLight = new THREE.DirectionalLight(0xffffff, 0.5);
        scene.add(directionalLight);
    }

    function render() {
        width = _get_width();
        height = _get_height();
        renderer.setSize(width, height);
        renderer.render(scene, camera);
    }

    let animate_id = requestAnimationFrame(animate);
    function animate() {
        if ($('#' + doc_canvas_id).length === 0) { // stop animate
            cancelAnimationFrame(animate_id);
            return;
        }

        if (rotated) {
            if ('x' === rotate_axis) {
                group.rotation.x -= rotate_speed;
            } else if ('y' === rotate_axis) {
                group.rotation.y -= rotate_speed;
            } else if ('z' === rotate_axis) {
                group.rotation.z -= rotate_speed;
            } else if ('-x' === rotate_axis) {
                group.rotation.x += rotate_speed;
            } else if ('-y' === rotate_axis) {
                group.rotation.y += rotate_speed;
            } else {
                group.rotation.z += rotate_speed;
            }
        }
        control.update();
        requestAnimationFrame(animate);
        render();
    }

    function init() {
        prepareRender();
        insertObj_normalize();
        insertOther();
        animate();
    }

    init();
}


function openSuccMsgBox (msg, duration=5000) {
    $('#succ-msg-box-body').html(msg)
    $('#succ-msg-box').modal('show');
    setTimeout(function() {
        $('#succ-msg-box').modal('hide');
    }, duration);
}

function openErrMsgBox (msg, duration=5000) {
    $('#err-msg-box-body').html(msg)
    $('#err-msg-box').modal('show');
    setTimeout(function() {
        $('#err-msg-box').modal('hide');
    }, duration);
}

function openLoadingBox (msg, progress_show=false) {
    if (!progress_show) {
        $('#progress-loading-box').hide();
    }
    $('#loading-body').html(msg)
    $('#loading').modal('show');
}

function closeLoadingBox() {
    $('#loading').modal('hide');
}

function objClone(obj) {
    return JSON.parse(JSON.stringify(obj));
}

function RGB2Hex(red, green, blue) {
    let hex = 0;
    hex += red;
    hex <<= 8;
    hex += green;
    hex <<= 8;
    hex += blue;
    return hex;
}
