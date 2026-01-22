<template>
  <div class="config-page">
    <div class="page-header">
      <div class="title">系统配置</div>
      <el-button type="primary" @click="handleAdd">
        <el-icon><Plus /></el-icon>
        添加配置
      </el-button>
    </div>

    <!-- 配置分类 -->
    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane label="基本配置" name="basic">
        <el-form :model="basicForm" label-width="160px">
          <el-form-item label="系统名称">
            <el-input v-model="basicForm.SYSTEM_NAME" placeholder="系统名称" />
          </el-form-item>
          <el-form-item label="时区">
            <el-select v-model="basicForm.TIMEZONE">
              <el-option label="Asia/Shanghai" value="Asia/Shanghai" />
              <el-option label="UTC" value="UTC" />
            </el-select>
          </el-form-item>
          <el-form-item label="维护模式">
            <el-switch v-model="basicForm.MAINTENANCE_MODE" />
            <span class="tip">开启后普通用户无法访问</span>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSaveBasic">保存基本配置</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="企业微信" name="wecom">
        <el-form :model="wecomForm" label-width="160px">
          <el-form-item label="CorpID">
            <el-input v-model="wecomForm.WECOM_CORPID" placeholder="企业微信 CorpID" />
          </el-form-item>
          <el-form-item label="App Secret">
            <el-input v-model="wecomForm.WECOM_APP_SECRET" type="password" placeholder="应用 Secret" show-password />
          </el-form-item>
          <el-form-item label="AgentID">
            <el-input-number v-model="wecomForm.WECOM_AGENTID" :min="0" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSaveWecom">保存企业微信配置</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="Craft" name="craft">
        <el-form :model="craftForm" label-width="160px">
          <el-form-item label="API Token">
            <el-input v-model="craftForm.CRAFT_API_TOKEN" type="password" placeholder="Craft API Token" show-password />
          </el-form-item>
          <el-form-item label="Links ID">
            <el-input v-model="craftForm.CRAFT_LINKS_ID" placeholder="Craft Links ID" />
          </el-form-item>
          <el-form-item label="待办文档 ID">
            <el-input v-model="craftForm.CRAFT_TODO_DOC_ID" placeholder="待办提醒文档 ID" />
          </el-form-item>
          <el-form-item label="启用待办提醒">
            <el-switch v-model="craftForm.CRAFT_TODO_ENABLED" />
          </el-form-item>
          <el-form-item label="提醒时间">
            <el-time-picker v-model="craftForm.CRAFT_TODO_REMIND_TIME" format="HH:mm" value-format="HH:mm" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSaveCraft">保存 Craft 配置</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="邮件" name="email">
        <el-form :model="emailForm" label-width="160px">
          <el-form-item label="SMTP 服务器">
            <el-input v-model="emailForm.EMAIL_SMTP_HOST" placeholder="smtp.example.com" />
          </el-form-item>
          <el-form-item label="SMTP 端口">
            <el-input-number v-model="emailForm.EMAIL_SMTP_PORT" :min="1" :max="65535" />
          </el-form-item>
          <el-form-item label="邮箱账号">
            <el-input v-model="emailForm.EMAIL_USERNAME" placeholder="your@email.com" />
          </el-form-item>
          <el-form-item label="授权码/密码">
            <el-input v-model="emailForm.EMAIL_PASSWORD" type="password" placeholder="授权码" show-password />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSaveEmail">保存邮件配置</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="自定义配置" name="custom">
        <el-table :data="customConfigs" v-loading="loading" stripe>
          <el-table-column prop="config_key" label="配置键" width="250" />
          <el-table-column prop="config_value" label="配置值" min-width="300">
            <template #default="{ row }">
              <el-input
                v-if="editingKey === row.config_key"
                v-model="editingValue"
                @keyup.enter="handleSaveCustom(row)"
              />
              <span v-else @dblclick="startEdit(row)" class="editable-value">
                {{ row.config_value }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="remark" label="备注" width="200" />
          <el-table-column label="操作" width="150">
            <template #default="{ row }">
              <el-button v-if="editingKey === row.config_key" type="success" link @click="handleSaveCustom(row)">保存</el-button>
              <el-button v-else type="primary" link @click="startEdit(row)">编辑</el-button>
              <el-button type="danger" link @click="handleDeleteCustom(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 添加配置弹窗 -->
    <el-dialog v-model="dialogVisible" title="添加配置" width="500px">
      <el-form ref="formRef" :model="newConfig" :rules="configRules" label-width="100px">
        <el-form-item label="配置键" prop="key">
          <el-input v-model="newConfig.key" placeholder="如: CUSTOM_KEY" />
        </el-form-item>
        <el-form-item label="配置值" prop="value">
          <el-input v-model="newConfig.value" placeholder="配置值" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="newConfig.remark" placeholder="备注说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAddConfig" :loading="saving">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import configApi from '@/api/config'

const activeTab = ref('basic')
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const formRef = ref(null)
const editingKey = ref('')
const editingValue = ref('')
const customConfigs = ref([])

const basicForm = reactive({
  SYSTEM_NAME: '',
  TIMEZONE: 'Asia/Shanghai',
  MAINTENANCE_MODE: false
})

const wecomForm = reactive({
  WECOM_CORPID: '',
  WECOM_APP_SECRET: '',
  WECOM_AGENTID: 0
})

const craftForm = reactive({
  CRAFT_API_TOKEN: '',
  CRAFT_LINKS_ID: '',
  CRAFT_TODO_DOC_ID: '',
  CRAFT_TODO_ENABLED: false,
  CRAFT_TODO_REMIND_TIME: '09:00'
})

const emailForm = reactive({
  EMAIL_SMTP_HOST: '',
  EMAIL_SMTP_PORT: 465,
  EMAIL_USERNAME: '',
  EMAIL_PASSWORD: ''
})

const newConfig = reactive({
  key: '',
  value: '',
  remark: ''
})

const configRules = {
  key: [{ required: true, message: '请输入配置键', trigger: 'blur' }],
  value: [{ required: true, message: '请输入配置值', trigger: 'blur' }]
}

onMounted(async () => {
  await Promise.all([loadBasic(), loadWecom(), loadCraft(), loadEmail(), loadCustom()])
})

async function loadBasic() {
  try {
    const res = await configApi.getAll()
    if (res.SYSTEM_NAME) basicForm.SYSTEM_NAME = res.SYSTEM_NAME
    if (res.TIMEZONE) basicForm.TIMEZONE = res.TIMEZONE
    if (res.MAINTENANCE_MODE !== undefined) basicForm.MAINTENANCE_MODE = res.MAINTENANCE_MODE
  } catch (e) {}
}

async function loadWecom() {
  try {
    const keys = ['WECOM_CORPID', 'WECOM_APP_SECRET', 'WECOM_AGENTID']
    for (const key of keys) {
      const val = await configApi.get(key)
      if (val !== null && wecomForm.hasOwnProperty(key)) {
        wecomForm[key] = val
      }
    }
  } catch (e) {}
}

async function loadCraft() {
  try {
    const keys = ['CRAFT_API_TOKEN', 'CRAFT_LINKS_ID', 'CRAFT_TODO_DOC_ID', 'CRAFT_TODO_ENABLED', 'CRAFT_TODO_REMIND_TIME']
    for (const key of keys) {
      const val = await configApi.get(key)
      if (val !== null) {
        if (key === 'CRAFT_TODO_ENABLED') {
          craftForm[key] = val === 'true' || val === true
        } else if (key === 'CRAFT_TODO_REMIND_TIME') {
          craftForm[key] = val
        } else {
          craftForm[key] = val
        }
      }
    }
  } catch (e) {}
}

async function loadEmail() {
  try {
    const keys = ['EMAIL_SMTP_HOST', 'EMAIL_SMTP_PORT', 'EMAIL_USERNAME', 'EMAIL_PASSWORD']
    for (const key of keys) {
      const val = await configApi.get(key)
      if (val !== null && emailForm.hasOwnProperty(key)) {
        emailForm[key] = val
      }
    }
  } catch (e) {}
}

async function loadCustom() {
  loading.value = true
  try {
    customConfigs.value = await configApi.list()
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function handleSaveBasic() {
  try {
    await configApi.set('SYSTEM_NAME', basicForm.SYSTEM_NAME)
    await configApi.set('TIMEZONE', basicForm.TIMEZONE)
    await configApi.set('MAINTENANCE_MODE', basicForm.MAINTENANCE_MODE)
    ElMessage.success('保存成功')
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

async function handleSaveWecom() {
  try {
    await configApi.set('WECOM_CORPID', wecomForm.WECOM_CORPID)
    await configApi.set('WECOM_APP_SECRET', wecomForm.WECOM_APP_SECRET)
    await configApi.set('WECOM_AGENTID', wecomForm.WECOM_AGENTID)
    ElMessage.success('保存成功')
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

async function handleSaveCraft() {
  try {
    await configApi.set('CRAFT_API_TOKEN', craftForm.CRAFT_API_TOKEN)
    await configApi.set('CRAFT_LINKS_ID', craftForm.CRAFT_LINKS_ID)
    await configApi.set('CRAFT_TODO_DOC_ID', craftForm.CRAFT_TODO_DOC_ID)
    await configApi.set('CRAFT_TODO_ENABLED', craftForm.CRAFT_TODO_ENABLED)
    await configApi.set('CRAFT_TODO_REMIND_TIME', craftForm.CRAFT_TODO_REMIND_TIME)
    ElMessage.success('保存成功')
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

async function handleSaveEmail() {
  try {
    await configApi.set('EMAIL_SMTP_HOST', emailForm.EMAIL_SMTP_HOST)
    await configApi.set('EMAIL_SMTP_PORT', emailForm.EMAIL_SMTP_PORT)
    await configApi.set('EMAIL_USERNAME', emailForm.EMAIL_USERNAME)
    await configApi.set('EMAIL_PASSWORD', emailForm.EMAIL_PASSWORD)
    ElMessage.success('保存成功')
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

function handleAdd() {
  newConfig.key = ''
  newConfig.value = ''
  newConfig.remark = ''
  dialogVisible.value = true
}

async function handleAddConfig() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      await configApi.set(newConfig.key, newConfig.value)
      if (newConfig.remark) {
        await configApi.set(`${newConfig.key}_REMARK`, newConfig.remark)
      }
      ElMessage.success('添加成功')
      dialogVisible.value = false
      loadCustom()
    } catch (e) {
      ElMessage.error('添加失败')
    } finally {
      saving.value = false
    }
  })
}

function startEdit(row) {
  editingKey.value = row.config_key
  editingValue.value = row.config_value
}

async function handleSaveCustom(row) {
  try {
    await configApi.set(row.config_key, editingValue.value)
    ElMessage.success('保存成功')
    editingKey.value = ''
    editingValue.value = ''
    loadCustom()
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

async function handleDeleteCustom(row) {
  try {
    await ElMessageBox.confirm(`确定删除配置 "${row.config_key}"？`, '确认删除', { type: 'warning' })
    await configApi.delete(row.config_key)
    ElMessage.success('删除成功')
    loadCustom()
  } catch (e) {
    if (e !== 'cancel') console.error(e)
  }
}
</script>

<style lang="scss" scoped>
.tip {
  margin-left: 8px;
  color: #909399;
  font-size: 12px;
}
.editable-value {
  cursor: pointer;
  &:hover {
    color: #409EFF;
  }
}
</style>
