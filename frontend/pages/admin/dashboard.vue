<template>
  <div class="space-y-8">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold bg-gradient-to-r from-cyan-600 to-blue-600 bg-clip-text text-transparent">
          管理后台
        </h1>
        <p class="text-gray-600 dark:text-gray-400 mt-1">
          欢迎回来，管理您的图床系统
        </p>
      </div>
      <div class="flex items-center gap-3">
        <UButton
          icon="heroicons:megaphone"
          color="blue"
          variant="soft"
          @click="announcementModalOpen = true"
        >
          公告管理
        </UButton>
        <UButton
          icon="heroicons:arrow-path"
          color="gray"
          variant="outline"
          @click="loadConfig"
        >
          刷新数据
        </UButton>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <UCard class="shadow-lg hover:shadow-xl transition-shadow">
        <div class="flex items-center gap-4">
          <div class="w-14 h-14 bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg">
            <UIcon name="heroicons:photo" class="w-7 h-7 text-white" />
          </div>
          <div class="flex-1">
            <p class="text-sm text-slate-600 dark:text-slate-400 mb-1">总图片数</p>
            <p class="text-3xl font-bold text-slate-900 dark:text-white">
              {{ stats.totalImages || '--' }}
            </p>
          </div>
        </div>
      </UCard>

      <UCard class="shadow-lg hover:shadow-xl transition-shadow">
        <div class="flex items-center gap-4">
          <div class="w-14 h-14 bg-gradient-to-br from-cyan-500 to-cyan-600 rounded-2xl flex items-center justify-center shadow-lg">
            <UIcon name="heroicons:cube" class="w-7 h-7 text-white" />
          </div>
          <div class="flex-1">
            <p class="text-sm text-slate-600 dark:text-slate-400 mb-1">总存储量</p>
            <p class="text-3xl font-bold text-slate-900 dark:text-white">
              {{ stats.totalSize || '--' }}
            </p>
          </div>
        </div>
      </UCard>

      <UCard class="shadow-lg hover:shadow-xl transition-shadow">
        <div class="flex items-center gap-4">
          <div class="w-14 h-14 bg-gradient-to-br from-blue-600 to-blue-700 rounded-2xl flex items-center justify-center shadow-lg">
            <UIcon name="heroicons:cloud-arrow-up" class="w-7 h-7 text-white" />
          </div>
          <div class="flex-1">
            <p class="text-sm text-slate-600 dark:text-slate-400 mb-1">今日上传</p>
            <p class="text-3xl font-bold text-slate-900 dark:text-white">
              {{ stats.todayUploads || '--' }}
            </p>
          </div>
        </div>
      </UCard>

      <UCard class="shadow-lg hover:shadow-xl transition-shadow">
        <div class="flex items-center gap-4">
          <div class="w-14 h-14 bg-gradient-to-br from-amber-500 to-amber-600 rounded-2xl flex items-center justify-center shadow-lg">
            <UIcon name="heroicons:bolt" class="w-7 h-7 text-white" />
          </div>
          <div class="flex-1">
            <p class="text-sm text-slate-600 dark:text-slate-400 mb-1">CDN缓存</p>
            <p class="text-3xl font-bold text-slate-900 dark:text-white">
              {{ stats.cdnCached || '--' }}
            </p>
          </div>
        </div>
      </UCard>
    </div>

    <!-- 系统配置 -->
    <UCard class="shadow-lg">
      <template #header>
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-green-500 to-green-600 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:cog-6-tooth" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-slate-900 dark:text-white">系统配置</h3>
              <p class="text-xs text-gray-500 dark:text-gray-400">当前系统运行状态</p>
            </div>
          </div>
        </div>
      </template>

      <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div class="p-4 bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-xl border border-green-200 dark:border-green-800">
          <div class="flex items-center gap-2 mb-2">
            <UIcon name="heroicons:signal" class="w-4 h-4 text-green-600 dark:text-green-400" />
            <p class="text-sm font-medium text-slate-600 dark:text-slate-400">CDN状态</p>
          </div>
          <p class="text-lg font-bold text-slate-900 dark:text-white">
            {{ systemConfig.cdnStatus || '--' }}
          </p>
        </div>
        <div class="p-4 bg-gradient-to-br from-blue-50 to-cyan-50 dark:from-blue-900/20 dark:to-cyan-900/20 rounded-xl border border-blue-200 dark:border-blue-800">
          <div class="flex items-center gap-2 mb-2">
            <UIcon name="heroicons:globe-alt" class="w-4 h-4 text-blue-600 dark:text-blue-400" />
            <p class="text-sm font-medium text-slate-600 dark:text-slate-400">CDN域名</p>
          </div>
          <p class="text-lg font-bold text-slate-900 dark:text-white truncate">
            {{ systemConfig.cdnDomain || '--' }}
          </p>
        </div>
        <div class="p-4 bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 rounded-xl border border-purple-200 dark:border-purple-800">
          <div class="flex items-center gap-2 mb-2">
            <UIcon name="heroicons:server" class="w-4 h-4 text-purple-600 dark:text-purple-400" />
            <p class="text-sm font-medium text-slate-600 dark:text-slate-400">存储类型</p>
          </div>
          <p class="text-lg font-bold text-slate-900 dark:text-white">
            Telegram Cloud
          </p>
        </div>
        <div class="p-4 bg-gradient-to-br from-orange-50 to-amber-50 dark:from-orange-900/20 dark:to-amber-900/20 rounded-xl border border-orange-200 dark:border-orange-800">
          <div class="flex items-center gap-2 mb-2">
            <UIcon name="heroicons:clock" class="w-4 h-4 text-orange-600 dark:text-orange-400" />
            <p class="text-sm font-medium text-slate-600 dark:text-slate-400">运行时间</p>
          </div>
          <p class="text-lg font-bold text-slate-900 dark:text-white">
            {{ systemConfig.uptime || '--' }}
          </p>
        </div>
        <div class="p-4 bg-gradient-to-br from-indigo-50 to-blue-50 dark:from-indigo-900/20 dark:to-blue-900/20 rounded-xl border border-indigo-200 dark:border-indigo-800">
          <div class="flex items-center gap-2 mb-2">
            <UIcon name="heroicons:user-group" class="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
            <p class="text-sm font-medium text-slate-600 dark:text-slate-400">群组上传</p>
          </div>
          <p class="text-lg font-bold text-slate-900 dark:text-white">
            {{ systemConfig.groupUpload || '--' }}
          </p>
        </div>
        <div class="p-4 bg-gradient-to-br from-teal-50 to-cyan-50 dark:from-teal-900/20 dark:to-cyan-900/20 rounded-xl border border-teal-200 dark:border-teal-800">
          <div class="flex items-center gap-2 mb-2">
            <UIcon name="heroicons:chart-bar" class="w-4 h-4 text-teal-600 dark:text-teal-400" />
            <p class="text-sm font-medium text-slate-600 dark:text-slate-400">CDN监控</p>
          </div>
          <p class="text-lg font-bold text-slate-900 dark:text-white">
            {{ systemConfig.cdnMonitor || '--' }}
          </p>
        </div>
      </div>
    </UCard>

    <!-- 操作栏 -->
    <UCard class="shadow-lg">
      <div class="flex flex-col md:flex-row md:items-center gap-4">
        <!-- 左侧：批量操作 -->
        <div class="flex items-center gap-3">
          <UCheckbox v-model="selectAll" @change="handleSelectAll">
            <template #label>
              <span class="text-sm font-medium">全选</span>
            </template>
          </UCheckbox>
          <UButton
            color="red"
            variant="soft"
            size="sm"
            :disabled="selectedImages.length === 0"
            @click="handleDeleteSelected"
          >
            <template #leading>
              <UIcon name="heroicons:trash" />
            </template>
            删除选中 ({{ selectedImages.length }})
          </UButton>
          <UButton
            color="yellow"
            variant="soft"
            size="sm"
            @click="handleClearCache"
          >
            <template #leading>
              <UIcon name="heroicons:arrow-path" />
            </template>
            清理缓存
          </UButton>
        </div>

        <!-- 右侧：筛选和搜索 -->
        <div class="flex items-center gap-2 md:ml-auto">
          <USelect
            v-model="filterType"
            :options="filterOptions"
            size="sm"
            @change="loadImages"
          />
          <UInput
            v-model="searchQuery"
            placeholder="搜索文件名..."
            size="sm"
            @input="handleSearch"
          >
            <template #leading>
              <UIcon name="heroicons:magnifying-glass" class="w-4 h-4" />
            </template>
          </UInput>
          <UButton
            icon="heroicons:arrow-path"
            color="gray"
            variant="ghost"
            size="sm"
            @click="loadImages"
          />
        </div>
      </div>
    </UCard>

    <!-- 图片网格 -->
    <UCard class="shadow-lg">
      <template #header>
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:photo" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-slate-900 dark:text-white">
                图片管理
              </h3>
              <p class="text-xs text-gray-500 dark:text-gray-400">
                共 {{ images.length }} 张图片
              </p>
            </div>
          </div>
        </div>
      </template>

      <div v-if="loading" class="flex flex-col justify-center items-center py-16">
        <div class="w-16 h-16 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mb-4"></div>
        <p class="text-gray-600 dark:text-gray-400">加载中...</p>
      </div>

      <div v-else-if="images.length === 0" class="text-center py-16">
        <div class="w-20 h-20 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
          <UIcon name="heroicons:photo" class="w-10 h-10 text-slate-400" />
        </div>
        <p class="text-lg font-medium text-slate-900 dark:text-white mb-2">暂无图片</p>
        <p class="text-sm text-slate-600 dark:text-slate-400">还没有上传任何图片</p>
      </div>

      <div v-else class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <div
          v-for="image in images"
          :key="image.id"
          class="relative group aspect-square rounded-xl overflow-hidden border-2 transition-all hover:shadow-lg"
          :class="[
            selectedImages.includes(image.id)
              ? 'border-cyan-500 ring-2 ring-cyan-500 ring-offset-2'
              : 'border-gray-200 dark:border-gray-700 hover:border-cyan-400'
          ]"
        >
          <img
            :src="image.url"
            :alt="image.filename"
            class="w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-300"
          />

          <!-- 选择框 -->
          <div class="absolute top-2 left-2 z-10">
            <div class="bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm rounded-lg p-1.5 shadow-lg">
              <UCheckbox
                :model-value="selectedImages.includes(image.id)"
                @change="toggleImageSelection(image.id)"
              />
            </div>
          </div>

          <!-- 缓存状态 -->
          <div v-if="image.cached" class="absolute top-2 right-2 z-10">
            <UBadge color="green" variant="solid" size="xs" class="shadow-lg">
              <template #leading>
                <UIcon name="heroicons:check-circle" class="w-3 h-3" />
              </template>
              已缓存
            </UBadge>
          </div>

          <!-- 操作按钮 -->
          <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
            <UButton
              icon="heroicons:eye"
              color="white"
              size="sm"
              @click="viewImageDetail(image)"
            />
            <UButton
              icon="heroicons:clipboard-document"
              color="white"
              size="sm"
              @click="copyImageUrl(image.url)"
            />
            <UButton
              icon="heroicons:trash"
              color="red"
              size="sm"
              @click="deleteImage(image.id)"
            />
          </div>

          <!-- 文件名提示 -->
          <div class="absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
            <p class="text-white text-xs truncate">{{ image.filename }}</p>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <template #footer>
        <div class="flex justify-center pt-4">
          <UPagination
            v-model="currentPage"
            :total="totalPages"
            @update:model-value="loadImages"
          />
        </div>
      </template>
    </UCard>

    <!-- 图片详情模态框 -->
    <UModal v-model="detailModalOpen">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">图片详情</h3>
            <UButton
              icon="heroicons:x-mark"
              color="gray"
              variant="ghost"
              @click="detailModalOpen = false"
            />
          </div>
        </template>

        <div v-if="selectedImage" class="space-y-4">
          <img
            :src="selectedImage.url"
            :alt="selectedImage.filename"
            class="w-full rounded-lg"
          />
          <div class="space-y-2 text-sm">
            <div class="flex justify-between">
              <span class="text-slate-600 dark:text-slate-400">文件名:</span>
              <span class="font-semibold">{{ selectedImage.filename }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-600 dark:text-slate-400">大小:</span>
              <span class="font-semibold">{{ selectedImage.size }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-600 dark:text-slate-400">上传时间:</span>
              <span class="font-semibold">{{ selectedImage.uploadTime }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-600 dark:text-slate-400">缓存状态:</span>
              <UBadge :color="selectedImage.cached ? 'green' : 'gray'" size="xs">
                {{ selectedImage.cached ? '已缓存' : '未缓存' }}
              </UBadge>
            </div>
            <div>
              <span class="text-slate-600 dark:text-slate-400">URL:</span>
              <code class="block mt-1 p-2 bg-gray-100 dark:bg-slate-800 rounded text-xs break-all">
                {{ selectedImage.url }}
              </code>
            </div>
          </div>
        </div>
      </UCard>
    </UModal>

    <!-- 删除确认模态框 -->
    <UModal v-model="deleteModalOpen">
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">确认删除</h3>
        </template>

        <p class="text-gray-700 dark:text-gray-300">
          {{ deleteMessage }}
        </p>

        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="deleteModalOpen = false">
              取消
            </UButton>
            <UButton color="red" @click="confirmDelete">
              确认删除
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- 公告管理模态框 -->
    <UModal v-model="announcementModalOpen" :ui="{ width: 'max-w-4xl' }">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-gradient-to-br from-blue-600 to-blue-700 rounded-lg flex items-center justify-center">
                <UIcon name="heroicons:megaphone" class="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-slate-900 dark:text-white">公告管理</h3>
                <p class="text-xs text-gray-500 dark:text-slate-400">管理系统公告内容和显示状态</p>
              </div>
            </div>
            <UButton
              icon="heroicons:x-mark"
              color="gray"
              variant="ghost"
              @click="announcementModalOpen = false"
            />
          </div>
        </template>

        <div class="space-y-6">
          <!-- 公告状态 -->
          <div class="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
            <div class="flex items-center gap-3">
              <UIcon
                :name="announcement.enabled ? 'heroicons:check-circle' : 'heroicons:x-circle'"
                :class="announcement.enabled ? 'text-green-500' : 'text-slate-400'"
                class="w-6 h-6"
              />
              <div>
                <p class="font-medium text-slate-900 dark:text-white">
                  {{ announcement.enabled ? '公告已启用' : '公告已禁用' }}
                </p>
                <p class="text-sm text-gray-500 dark:text-slate-400">
                  {{ announcement.enabled ? '用户访问网站时会看到此公告' : '公告不会显示给用户' }}
                </p>
              </div>
            </div>
            <UToggle v-model="announcement.enabled" size="lg" />
          </div>

          <!-- 公告内容编辑 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              公告内容 (支持HTML)
            </label>
            <UTextarea
              v-model="announcement.content"
              :rows="10"
              placeholder="请输入公告内容，支持HTML格式..."
              class="font-mono text-sm"
            />
            <p class="text-xs text-gray-500 dark:text-slate-400 mt-2">
              提示：可以使用HTML标签来格式化内容，例如 &lt;strong&gt;、&lt;p&gt;、&lt;ul&gt; 等
            </p>
          </div>

          <!-- 快速模板 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              快速模板
            </label>
            <div class="grid grid-cols-3 gap-2">
              <UButton
                v-for="(template, index) in announcementTemplates"
                :key="index"
                size="sm"
                color="gray"
                variant="soft"
                @click="useAnnouncementTemplate(template.content)"
              >
                {{ template.name }}
              </UButton>
            </div>
          </div>

          <!-- 预览 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              预览效果
            </label>
            <div class="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-4">
              <div
                v-if="announcement.content"
                class="prose dark:prose-invert max-w-none text-sm"
                v-html="announcement.content"
              ></div>
              <div v-else class="text-center py-4 text-gray-500 text-sm">
                暂无公告内容
              </div>
            </div>
          </div>

          <!-- 公告信息 -->
          <div v-if="announcement.id" class="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <div>
              <p class="text-xs text-gray-500 dark:text-slate-400">创建时间</p>
              <p class="text-sm font-medium text-slate-900 dark:text-white">
                {{ formatDate(announcement.created_at) }}
              </p>
            </div>
            <div>
              <p class="text-xs text-gray-500 dark:text-slate-400">更新时间</p>
              <p class="text-sm font-medium text-slate-900 dark:text-white">
                {{ formatDate(announcement.updated_at) }}
              </p>
            </div>
          </div>
        </div>

        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton
              color="gray"
              variant="ghost"
              @click="resetAnnouncement"
            >
              重置
            </UButton>
            <UButton
              color="primary"
              :loading="savingAnnouncement"
              @click="saveAnnouncement"
            >
              保存公告
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'admin',
  middleware: 'auth'
})

const runtimeConfig = useRuntimeConfig()
const notification = useNotification()
const { getAdminStats, getImages, deleteImages, clearCache } = useImageApi()

// 状态
const loading = ref(false)
const stats = ref<any>({})
const systemConfig = ref<any>({})
const images = ref<any[]>([])
const selectedImages = ref<number[]>([])
const selectAll = ref(false)
const filterType = ref('all')
const searchQuery = ref('')
const currentPage = ref(1)
const totalPages = ref(1)
const detailModalOpen = ref(false)
const deleteModalOpen = ref(false)
const selectedImage = ref<any>(null)
const deleteMessage = ref('')
const deleteTarget = ref<'single' | 'multiple'>('single')

// 公告管理状态
const announcementModalOpen = ref(false)
const savingAnnouncement = ref(false)
const announcement = ref({
  id: 0,
  enabled: true,
  content: '',
  created_at: null,
  updated_at: null
})
const originalAnnouncement = ref<any>(null)

const filterOptions = [
  { label: '全部图片', value: 'all' },
  { label: '已缓存', value: 'cached' },
  { label: '未缓存', value: 'uncached' },
  { label: '群组上传', value: 'group' }
]

// 公告模板
const announcementTemplates = [
  {
    name: '欢迎公告',
    content: `<div class="space-y-4">
  <h3 class="text-xl font-bold text-slate-900 dark:text-white">欢迎使用 Telegram 云图床</h3>
  <div class="space-y-2 text-gray-700 dark:text-gray-300">
    <p>🎉 <strong>无限制使用：</strong>无上传数量限制，无时间限制</p>
    <p>🚀 <strong>CDN加速：</strong>全球CDN加速，访问更快</p>
    <p>🔒 <strong>安全可靠：</strong>基于Telegram云存储，永久保存</p>
    <p>💎 <strong>Token模式：</strong>生成专属Token，管理您的图片</p>
  </div>
</div>`
  },
  {
    name: '维护通知',
    content: `<div class="space-y-3">
  <h3 class="text-xl font-bold text-red-600 dark:text-red-400">系统维护通知</h3>
  <p class="text-gray-700 dark:text-gray-300">
    系统将于 <strong>2024年12月1日 22:00-23:00</strong> 进行维护升级，期间服务可能会短暂中断。
  </p>
  <p class="text-gray-700 dark:text-gray-300">
    维护期间已上传的图片不受影响，请合理安排上传时间。感谢您的理解与支持！
  </p>
</div>`
  },
  {
    name: '功能更新',
    content: `<div class="space-y-3">
  <h3 class="text-xl font-bold text-blue-600 dark:text-blue-400">新功能上线</h3>
  <p class="text-gray-700 dark:text-gray-300">我们很高兴地宣布以下新功能已上线：</p>
  <ul class="list-disc list-inside space-y-1 text-gray-700 dark:text-gray-300">
    <li>支持批量上传图片</li>
    <li>新增图片压缩功能</li>
    <li>优化CDN加速性能</li>
    <li>支持自定义Token管理</li>
  </ul>
  <p class="text-gray-700 dark:text-gray-300">快来体验吧！</p>
</div>`
  }
]

// 加载统计信息
const loadStats = async () => {
  try {
    const data = await getAdminStats()
    stats.value = data.stats
    systemConfig.value = data.config
  } catch (error) {
    console.error('加载统计信息失败:', error)
  }
}

// 加载配置
const loadConfig = async () => {
  await loadStats()
  notification.success('已刷新', '配置信息已更新')
}

// 加载图片列表
const loadImages = async () => {
  loading.value = true
  try {
    const data = await getImages({
      page: currentPage.value,
      filter: filterType.value,
      search: searchQuery.value
    })
    images.value = data.images
    totalPages.value = data.totalPages
  } catch (error) {
    notification.error('错误', '加载图片列表失败')
  } finally {
    loading.value = false
  }
}

// 搜索处理
const handleSearch = useDebounceFn(() => {
  currentPage.value = 1
  loadImages()
}, 500)

// 全选处理
const handleSelectAll = () => {
  if (selectAll.value) {
    selectedImages.value = images.value.map(img => img.id)
  } else {
    selectedImages.value = []
  }
}

// 切换图片选择
const toggleImageSelection = (id: number) => {
  const index = selectedImages.value.indexOf(id)
  if (index > -1) {
    selectedImages.value.splice(index, 1)
  } else {
    selectedImages.value.push(id)
  }
}

// 查看图片详情
const viewImageDetail = (image: any) => {
  selectedImage.value = image
  detailModalOpen.value = true
}

// 复制图片 URL
const copyImageUrl = async (url: string) => {
  await navigator.clipboard.writeText(url)
  notification.success('已复制', 'URL 已复制到剪贴板')
}

// 删除单个图片
const deleteImage = (id: number) => {
  selectedImages.value = [id]
  deleteTarget.value = 'single'
  deleteMessage.value = '确定要删除这张图片吗？此操作不可恢复。'
  deleteModalOpen.value = true
}

// 删除选中图片
const handleDeleteSelected = () => {
  deleteTarget.value = 'multiple'
  deleteMessage.value = `确定要删除选中的 ${selectedImages.value.length} 张图片吗？此操作不可恢复。`
  deleteModalOpen.value = true
}

// 确认删除
const confirmDelete = async () => {
  try {
    await deleteImages(selectedImages.value)
    notification.success('删除成功', `已删除 ${selectedImages.value.length} 张图片`)
    selectedImages.value = []
    selectAll.value = false
    deleteModalOpen.value = false
    await loadImages()
    await loadStats()
  } catch (error) {
    notification.error('删除失败', '删除图片时出错')
  }
}

// 清理缓存
const handleClearCache = async () => {
  try {
    await clearCache()
    notification.success('成功', '缓存已清理')
    await loadStats()
  } catch (error) {
    notification.error('错误', '清理缓存失败')
  }
}

// ==================== 公告管理功能 ====================

// 加载公告
const loadAnnouncement = async () => {
  try {
    const response = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/announcement`, {
      credentials: 'include'
    })

    if (response.success && response.data) {
      announcement.value = { ...response.data }
      originalAnnouncement.value = { ...response.data }
    }
  } catch (error: any) {
    console.error('加载公告失败:', error)
    notification.error('加载失败', error.data?.error || '无法加载公告信息')
  }
}

// 保存公告
const saveAnnouncement = async () => {
  if (!announcement.value.content.trim()) {
    notification.warning('提示', '请输入公告内容')
    return
  }

  savingAnnouncement.value = true
  try {
    const response = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/announcement`, {
      method: 'POST',
      credentials: 'include',
      body: {
        enabled: announcement.value.enabled,
        content: announcement.value.content
      }
    })

    if (response.success) {
      notification.success('保存成功', '公告已更新')
      await loadAnnouncement()
      announcementModalOpen.value = false
    }
  } catch (error: any) {
    console.error('保存公告失败:', error)
    notification.error('保存失败', error.data?.error || '无法保存公告')
  } finally {
    savingAnnouncement.value = false
  }
}

// 重置公告
const resetAnnouncement = () => {
  if (originalAnnouncement.value) {
    announcement.value = { ...originalAnnouncement.value }
  }
  notification.info('已重置', '公告内容已恢复')
}

// 使用模板
const useAnnouncementTemplate = (content: string) => {
  announcement.value.content = content
  notification.success('模板已应用', '您可以继续编辑内容')
}

// 格式化日期
const formatDate = (dateString: string | null) => {
  if (!dateString) return '--'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 监听公告模态框打开，自动加载公告
watch(announcementModalOpen, (isOpen) => {
  if (isOpen) {
    loadAnnouncement()
  }
})

// 页面加载
onMounted(() => {
  loadStats()
  loadImages()
})
</script>
