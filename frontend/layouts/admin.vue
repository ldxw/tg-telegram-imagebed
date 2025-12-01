<template>
  <div class="min-h-screen bg-stone-50 dark:bg-neutral-900">
    <!-- 顶部导航栏 -->
    <header class="sticky top-0 z-50 backdrop-blur-md bg-white/70 dark:bg-neutral-900/70 border-b border-stone-200/40 dark:border-neutral-700/40">
      <div class="container mx-auto px-4 py-3">
        <div class="flex items-center justify-between">
          <!-- Logo -->
          <NuxtLink to="/" class="flex items-center gap-2.5">
            <div class="w-9 h-9 bg-gradient-to-br from-amber-500 to-orange-500 rounded-lg flex items-center justify-center">
              <UIcon name="heroicons:cloud-arrow-up" class="w-5 h-5 text-white" />
            </div>
            <div class="flex items-center gap-2">
              <span class="text-lg font-semibold text-stone-800 dark:text-stone-100">图床 Pro</span>
              <UBadge color="red" variant="subtle" size="xs">管理</UBadge>
            </div>
          </NuxtLink>

          <!-- 用户操作 -->
          <div v-if="authStore.isAuthenticated" class="flex items-center gap-3">
            <span class="text-sm text-stone-600 dark:text-stone-400">
              {{ authStore.username }}
            </span>
            <button
              @click="settingsOpen = true"
              class="p-2 text-stone-600 dark:text-stone-300 hover:bg-stone-100/50 dark:hover:bg-neutral-800/50 rounded-md transition-all"
            >
              <UIcon name="heroicons:cog-6-tooth" class="w-5 h-5" />
            </button>
            <button
              @click="handleLogout"
              class="p-2 text-stone-600 dark:text-stone-300 hover:bg-stone-100/50 dark:hover:bg-neutral-800/50 rounded-md transition-all"
            >
              <UIcon name="heroicons:arrow-right-on-rectangle" class="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="container mx-auto px-4 py-8">
      <slot />
    </main>

    <!-- 设置模态框 -->
    <UModal v-model="settingsOpen">
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">管理员设置</h3>
        </template>

        <div class="space-y-4">
          <UFormGroup label="新用户名">
            <UInput v-model="settingsForm.username" placeholder="留空则不修改" />
          </UFormGroup>
          <UFormGroup label="新密码">
            <UInput v-model="settingsForm.password" type="password" placeholder="留空则不修改" />
          </UFormGroup>
          <UFormGroup label="确认密码">
            <UInput v-model="settingsForm.confirmPassword" type="password" placeholder="再次输入新密码" />
          </UFormGroup>
        </div>

        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="settingsOpen = false">
              取消
            </UButton>
            <UButton color="primary" @click="handleUpdateSettings">
              保存
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
const authStore = useAuthStore()
const notification = useNotification()

const settingsOpen = ref(false)
const settingsForm = ref({
  username: '',
  password: '',
  confirmPassword: ''
})


const handleLogout = async () => {
  await authStore.logout()
  navigateTo('/admin')
}

const handleUpdateSettings = async () => {
  if (settingsForm.value.password && settingsForm.value.password !== settingsForm.value.confirmPassword) {
    notification.error('错误', '两次输入的密码不一致')
    return
  }

  try {
    await authStore.updateSettings(settingsForm.value)
    notification.success('成功', '设置已更新')
    settingsOpen.value = false
    settingsForm.value = { username: '', password: '', confirmPassword: '' }
  } catch (error) {
    notification.error('错误', '更新设置失败')
  }
}
</script>
