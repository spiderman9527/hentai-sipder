### 绅士资源爬虫

#### 1.创建虚拟环境
创建虚拟环境并开启
```bash
python -m venv [venv-folder]
```
开启虚拟环境：
```bash
[venv-folder]/Scripts/activate
```
关闭虚拟环境（当退出项目时再执行也不迟）：
```bash
[venv-folder]/Scripts/deactivate
```
> 该步骤是为了隔离环境，如果你使用全局安装可跳过该步骤，请先确保系统已安装了python

#### 2. 安装依赖
```shell
pip install -r requirements.txt
```
#### 3. 启动程序

```bash
python src/main.py
```

#### 4. 使用
`website` 文件夹下存放的就是每个站点的爬虫代码，几乎每个站点文件夹都有各自的 `config.json`，用以调整不同站点的爬取规则，也可对下载做相关的配置，比如**下载文件夹目录**，以 `www_jpq_me` 为例,可通过修改 `config.json` 里 `download_dir` 的值完成配置，其他的内容可暂时不用处理。

#### 5. 拓展
每个站点的爬取都是基于 `BaseParser` 去实现的，新站点的爬取开发，可以通过继承 `BaseParser` 基类去实现，可以缩短一定的开发时间。

#### 6. 站点列表
- [https://www.jpq.me（优化中）](https://www.jpq.me)
- [https://akuma.moe（计划中）](https://akuma.moe)
