<template>
  <div class="max-w-4xl mx-auto space-y-8 pt-4">
    <div class="text-center space-y-4">
      <h1 class="text-4xl font-bold bg-gradient-to-r from-amber-600 to-orange-500 bg-clip-text text-transparent">
        API 文档
      </h1>
      <p class="text-stone-600 dark:text-stone-400">
        使用我们的 API 轻松集成图片上传功能
      </p>
    </div>

    <!-- 快速开始 -->
    <UCard>
      <template #header>
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white">快速开始</h2>
      </template>

      <div class="space-y-4">
        <p class="text-gray-700 dark:text-gray-300">
          我们的 API 提供简单易用的图片上传服务。所有请求都使用 HTTP POST 方法。
        </p>

        <div>
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">基础 URL</h3>
          <code class="block p-3 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm">
            {{ config.public.apiBase }}
          </code>
        </div>
      </div>
    </UCard>

    <!-- 上传图片 -->
    <UCard>
      <template #header>
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white">上传图片</h2>
      </template>

      <div class="space-y-6">
        <div>
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">端点</h3>
          <div class="flex items-center gap-2">
            <UBadge color="green" size="lg">POST</UBadge>
            <code class="text-sm">/upload</code>
          </div>
        </div>

        <div>
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">请求参数</h3>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead class="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th class="px-4 py-2 text-left">参数名</th>
                  <th class="px-4 py-2 text-left">类型</th>
                  <th class="px-4 py-2 text-left">必填</th>
                  <th class="px-4 py-2 text-left">说明</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
                <tr>
                  <td class="px-4 py-2"><code>file</code></td>
                  <td class="px-4 py-2">File</td>
                  <td class="px-4 py-2">是</td>
                  <td class="px-4 py-2">要上传的图片文件</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">请求示例</h3>
          <UTabs :items="codeTabs" class="w-full">
            <template #item="{ item }">
              <pre class="p-4 bg-gray-900 text-gray-100 rounded-lg overflow-x-auto text-sm"><code>{{ item.code }}</code></pre>
            </template>
          </UTabs>
        </div>

        <div>
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">响应示例</h3>
          <pre class="p-4 bg-gray-900 text-gray-100 rounded-lg overflow-x-auto text-sm"><code>{{ responseExample }}</code></pre>
        </div>
      </div>
    </UCard>

    <!-- 获取图片信息 -->
    <UCard>
      <template #header>
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white">获取图片信息</h2>
      </template>

      <div class="space-y-6">
        <div>
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">端点</h3>
          <div class="flex items-center gap-2">
            <UBadge color="blue" size="lg">GET</UBadge>
            <code class="text-sm">/api/stats</code>
          </div>
        </div>

        <div>
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">响应示例</h3>
          <pre class="p-4 bg-gray-900 text-gray-100 rounded-lg overflow-x-auto text-sm"><code>{{ statsExample }}</code></pre>
        </div>
      </div>
    </UCard>

    <!-- 错误代码 -->
    <UCard>
      <template #header>
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white">错误代码</h2>
      </template>

      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 dark:bg-gray-800">
            <tr>
              <th class="px-4 py-2 text-left">状态码</th>
              <th class="px-4 py-2 text-left">说明</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            <tr>
              <td class="px-4 py-2"><code>200</code></td>
              <td class="px-4 py-2">请求成功</td>
            </tr>
            <tr>
              <td class="px-4 py-2"><code>400</code></td>
              <td class="px-4 py-2">请求参数错误</td>
            </tr>
            <tr>
              <td class="px-4 py-2"><code>401</code></td>
              <td class="px-4 py-2">未授权</td>
            </tr>
            <tr>
              <td class="px-4 py-2"><code>413</code></td>
              <td class="px-4 py-2">文件过大</td>
            </tr>
            <tr>
              <td class="px-4 py-2"><code>500</code></td>
              <td class="px-4 py-2">服务器错误</td>
            </tr>
          </tbody>
        </table>
      </div>
    </UCard>

    <!-- 使用说明 -->
    <UCard>
      <template #header>
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white">使用说明</h2>
      </template>

      <ul class="space-y-2 text-gray-700 dark:text-gray-300">
        <li class="flex items-start gap-2">
          <UIcon name="heroicons:check-circle" class="w-5 h-5 text-green-500 mt-0.5" />
          <span>单个文件最大 20MB</span>
        </li>
        <li class="flex items-start gap-2">
          <UIcon name="heroicons:check-circle" class="w-5 h-5 text-green-500 mt-0.5" />
          <span>支持格式：JPG、PNG、GIF、WEBP</span>
        </li>
        <li class="flex items-start gap-2">
          <UIcon name="heroicons:check-circle" class="w-5 h-5 text-green-500 mt-0.5" />
          <span>无上传数量限制</span>
        </li>
        <li class="flex items-start gap-2">
          <UIcon name="heroicons:check-circle" class="w-5 h-5 text-green-500 mt-0.5" />
          <span>Token永久有效，无时间限制</span>
        </li>
        <li class="flex items-start gap-2">
          <UIcon name="heroicons:check-circle" class="w-5 h-5 text-green-500 mt-0.5" />
          <span>图片永久存储，不会过期</span>
        </li>
      </ul>
    </UCard>

    <!-- 在线测试 -->
    <UCard>
      <template #header>
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white">在线测试</h2>
      </template>

      <div class="space-y-4">
        <p class="text-gray-700 dark:text-gray-300">
          选择一张图片测试 API 上传功能
        </p>

        <div>
          <input
            ref="testFileInput"
            type="file"
            accept="image/*"
            class="hidden"
            @change="handleTestUpload"
          />
          <UButton
            icon="heroicons:cloud-arrow-up"
            color="primary"
            size="lg"
            :loading="testUploading"
            @click="testFileInput?.click()"
          >
            选择图片测试
          </UButton>
        </div>

        <div v-if="testResult" class="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <h4 class="font-semibold text-gray-900 dark:text-white mb-2">测试结果</h4>
          <pre class="text-sm overflow-x-auto"><code>{{ JSON.stringify(testResult, null, 2) }}</code></pre>
        </div>
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
const config = useRuntimeConfig()
const toast = useToast()
const { uploadImages } = useImageApi()

const testFileInput = ref<HTMLInputElement>()
const testUploading = ref(false)
const testResult = ref<any>(null)

const codeTabs = [
  {
    label: 'cURL',
    code: `curl -X POST ${config.public.apiBase}/upload \\
  -F "file=@/path/to/image.jpg"`
  },
  {
    label: 'JavaScript',
    code: `const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('${config.public.apiBase}/upload', {
  method: 'POST',
  body: formData
})
.then(res => res.json())
.then(data => console.log(data));`
  },
  {
    label: 'Python',
    code: `import requests

files = {'file': open('image.jpg', 'rb')}
response = requests.post(
    '${config.public.apiBase}/upload',
    files=files
)
print(response.json())`
  },
  {
    label: 'PHP',
    code: `<?php
$ch = curl_init();
$file = new CURLFile('image.jpg');
$data = array('file' => $file);

curl_setopt($ch, CURLOPT_URL, '${config.public.apiBase}/upload');
curl_setopt($ch, CURLOPT_POST, 1);
curl_setopt($ch, CURLOPT_POSTFIELDS, $data);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);
curl_close($ch);

echo $response;
?>`
  }
]

const responseExample = `{
  "success": true,
  "data": {
    "url": "https://example.com/image/abc123",
    "filename": "image.jpg",
    "size": "1.2 MB",
    "upload_time": "2024-01-01 12:00:00"
  }
}`

const statsExample = `{
  "success": true,
  "data": {
    "total_files": 1234,
    "total_size": "5.6 GB",
    "today_uploads": 56,
    "uptime": "30天"
  }
}`

const handleTestUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement
  if (!target.files || target.files.length === 0) return

  testUploading.value = true
  testResult.value = null

  try {
    const results = await uploadImages([target.files[0]])
    testResult.value = {
      success: true,
      data: results[0]
    }
    toast.add({
      title: '测试成功',
      description: '图片上传成功',
      color: 'green'
    })
  } catch (error: any) {
    testResult.value = {
      success: false,
      error: error.message
    }
    toast.add({
      title: '测试失败',
      description: error.message,
      color: 'red'
    })
  } finally {
    testUploading.value = false
  }
}
</script>
