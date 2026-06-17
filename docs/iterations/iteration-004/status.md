# Iteration 004 Status：统一偏好信号摄取

## 当前状态

```text
项目状态：暂停 / 暂时终止。
Build：已完成阶段性实现。
本地验证：通过。
远端 Hermes CLI 验证：通过。
Telegram 外部入站推荐验证：通过。
Telegram 外部入站反馈验证：未通过。
Closeout：未完成。
```

## 关键结果

```text
1. record_preference_signal 已作为优先入口暴露给 Hermes。
2. record_feedback 保留为 legacy compatibility entrypoint。
3. 普通兴趣真实会话已通过 record_preference_signal 生效。
4. 默认候选反馈真实会话也已切到 record_preference_signal。
5. TasteMate profile 更新和后续 rank_candidates 消费已在 CLI / hook 级验证中通过。
6. Telegram 推荐入站可触发 tastemate-route 后置重排。
7. Telegram 反馈入站未能写入 profile，原因是用户可见候选与插件保存候选上下文不一致。
```

## 结论

```text
当前不进入 Closeout。
项目按阶段性成果备份，后续如恢复，应优先解决真实候选上下文与用户可见推荐结果的一致性问题。
```
