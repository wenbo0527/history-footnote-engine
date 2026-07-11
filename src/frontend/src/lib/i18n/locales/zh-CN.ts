/**
 * 🆕 v2.10.x W52: 中文翻译字典
 *
 * 嵌套 key 用 . 分隔
 * 例：{ "nav.main.game": "游戏" }
 */
export const zh_CN: Record<string, string> = {
  // nav (导航)
  'nav.main.game': '游戏',
  'nav.main.wizard': '创建角色',
  'nav.main.archives': '存档',
  'nav.main.settings': '设置',
  'nav.action.refresh': '换一批',
  'nav.action.send': '发送',
  'nav.action.cancel': '取消',
  'nav.action.close': '关闭',
  'nav.action.confirm': '确认',

  // 状态
  'status.loading': '加载中...',
  'status.error': '出错了',
  'status.success': '成功',
  'status.empty': '暂无数据',
  'status.connected': '已连接',
  'status.disconnected': '未连接',

  // 章节
  'chapter.label': '第 {n} 章',
  'chapter.progress': '进度',
  'chapter.summary': '摘要',
  'chapter.events': '事件',
  'chapter.duration': '{n} 轮',
  'chapter.softReady': '软收束',
  'chapter.hardForced': '强制收尾',

  // 板块
  'plate.title': '板块格局',
  'plate.status.stable': '稳定',
  'plate.status.tense': '紧张',
  'plate.status.shifting': '变化',
  'plate.status.collapsed': '崩溃',
  'plate.tension': '张力',
  'plate.active': '激变中',

  // 性能监控
  'metrics.title': '性能监控',
  'metrics.uptime': '运行时间',
  'metrics.endpoints': '总端点',
  'metrics.tokens': '总 Token',
  'metrics.llmProviders': 'LLM Provider',
  'metrics.slowest': '最慢端点',
  'metrics.llm': 'LLM Provider',
  'metrics.errors': '错误率热点',

  // 存档
  'archives.title': '存档列表',
  'archives.empty': '暂无存档',
  'archives.continue': '继续',
  'archives.delete': '删除',
  'archives.deleteConfirm': '确认删除？',
  'archives.archived': '已归档',

  // 角色
  'char.name': '姓名',
  'char.family': '家世',
  'char.skills': '技能',
  'char.identity': '身份',

  // 错误
  'error.network': '网络错误',
  'error.notFound': '未找到',
  'error.unauthorized': '未授权',
  'error.serverError': '服务器错误',

  // 通用
  'common.yes': '是',
  'common.no': '否',
  'common.ok': '好',
  'common.save': '保存',
  'common.cancel': '取消',
  'common.delete': '删除',
  'common.edit': '编辑',
  'common.add': '添加',
  'common.search': '搜索',
  'common.filter': '筛选',

  // Admin
  'admin.title': 'Admin 模式',
  'admin.close': '关闭',
  'admin.toggle': '切换 admin 模式',
};
