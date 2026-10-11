# CI 构建日志

- 运行: #6
- 提交: `8dbc802110a6663fcf489d0749a176b9e8278d32`
- 事件: push
- 结果: build=failure verify=skipped package=skipped

## 工具链
```
Xcode 16.2
Build version 16C5032a
xcode-select: /Applications/Xcode_16.2.0.app/Contents/Developer
```

## Build
```
Command line invocation:
    /Applications/Xcode_16.2.app/Contents/Developer/usr/bin/xcodebuild -project UdpCast.xcodeproj -scheme UdpCast -configuration Release -sdk iphoneos -destination generic/platform=iOS -derivedDataPath build ONLY_ACTIVE_ARCH=NO CODE_SIGN_IDENTITY= CODE_SIGNING_REQUIRED=NO CODE_SIGNING_ALLOWED=NO ENABLE_BITCODE=NO build

User defaults from command line:
    IDEDerivedDataPathOverride = /Users/runner/work/232323/232323/ios/build
    IDEPackageSupportUseBuiltinSCM = YES

Build settings from command line:
    CODE_SIGN_IDENTITY = 
    CODE_SIGNING_ALLOWED = NO
    CODE_SIGNING_REQUIRED = NO
    ENABLE_BITCODE = NO
    ONLY_ACTIVE_ARCH = NO
    SDKROOT = iphoneos18.2

Prepare packages

note: Using codesigning identity override: 
ComputeTargetDependencyGraph
note: Building targets in dependency order
note: Target dependency graph (2 targets)
    Target 'UdpCast' in project 'UdpCast'
        ➜ Explicit dependency on target 'BroadcastExtension' in project 'UdpCast'
    Target 'BroadcastExtension' in project 'UdpCast' (no dependencies)

GatherProvisioningInputs

CreateBuildDescription

ExecuteExternalTool /Applications/Xcode_16.2.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc --version

ExecuteExternalTool /Applications/Xcode_16.2.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang -v -E -dM -isysroot /Applications/Xcode_16.2.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS18.2.sdk -x c -c /dev/null

ExecuteExternalTool /Applications/Xcode_16.2.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/ld -version_details

Build description signature: fbf23690ccc71354e5c74d02848d0185
Build description path: /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/XCBuildData/fbf23690ccc71354e5c74d02848d0185.xcbuilddata
CreateBuildDirectory /Users/runner/work/232323/232323/ios/build/Build/Products
    cd /Users/runner/work/232323/232323/ios/UdpCast.xcodeproj
    builtin-create-build-directory /Users/runner/work/232323/232323/ios/build/Build/Products

CreateBuildDirectory /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex
    cd /Users/runner/work/232323/232323/ios/UdpCast.xcodeproj
    builtin-create-build-directory /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex

ClangStatCache /Applications/Xcode_16.2.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang-stat-cache /Applications/Xcode_16.2.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS18.2.sdk /Users/runner/work/232323/232323/ios/build/SDKStatCaches.noindex/iphoneos18.2-22C146-6f6929c68f51360d5ca70a73a7e0c2f9.sdkstatcache
    cd /Users/runner/work/232323/232323/ios/UdpCast.xcodeproj
    /Applications/Xcode_16.2.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang-stat-cache /Applications/Xcode_16.2.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS18.2.sdk -o /Users/runner/work/232323/232323/ios/build/SDKStatCaches.noindex/iphoneos18.2-22C146-6f6929c68f51360d5ca70a73a7e0c2f9.sdkstatcache

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast-71caa62a2ca16e4dd353e8d2bf609973-VFS-iphoneos/all-product-headers.yaml
    cd /Users/runner/work/232323/232323/ios/UdpCast.xcodeproj
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast-71caa62a2ca16e4dd353e8d2bf609973-VFS-iphoneos/all-product-headers.yaml

CreateBuildDirectory /Users/runner/work/232323/232323/ios/build/Build/Products/Release-iphoneos
    cd /Users/runner/work/232323/232323/ios/UdpCast.xcodeproj
    builtin-create-build-directory /Users/runner/work/232323/232323/ios/build/Build/Products/Release-iphoneos

CreateBuildDirectory /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/EagerLinkingTBDs/Release-iphoneos
    cd /Users/runner/work/232323/232323/ios/UdpCast.xcodeproj
    builtin-create-build-directory /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/EagerLinkingTBDs/Release-iphoneos

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/UdpCast.DependencyMetadataFileList (in target 'UdpCast' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/UdpCast.DependencyMetadataFileList

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/UdpCast.hmap (in target 'UdpCast' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/UdpCast.hmap

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/UdpCast-project-headers.hmap (in target 'UdpCast' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/UdpCast-project-headers.hmap

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/UdpCast-own-target-headers.hmap (in target 'UdpCast' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/UdpCast-own-target-headers.hmap

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/UdpCast-generated-files.hmap (in target 'UdpCast' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/UdpCast-generated-files.hmap

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/UdpCast-all-target-headers.hmap (in target 'UdpCast' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/UdpCast-all-target-headers.hmap

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/UdpCast-all-non-framework-target-headers.hmap (in target 'UdpCast' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/UdpCast-all-non-framework-target-headers.hmap

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/Objects-normal/arm64/UdpCast_const_extract_protocols.json (in target 'UdpCast' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/Objects-normal/arm64/UdpCast_const_extract_protocols.json

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/Objects-normal/arm64/UdpCast.SwiftFileList (in target 'UdpCast' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/Objects-normal/arm64/UdpCast.SwiftFileList

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/Objects-normal/arm64/UdpCast.SwiftConstValuesFileList (in target 'UdpCast' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/Objects-normal/arm64/UdpCast.SwiftConstValuesFileList

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/Objects-normal/arm64/UdpCast.LinkFileList (in target 'UdpCast' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/Objects-normal/arm64/UdpCast.LinkFileList

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/Objects-normal/arm64/UdpCast-OutputFileMap.json (in target 'UdpCast' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/UdpCast.build/Objects-normal/arm64/UdpCast-OutputFileMap.json

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/BroadcastExtension_const_extract_protocols.json (in target 'BroadcastExtension' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/BroadcastExtension_const_extract_protocols.json

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/BroadcastExtension.SwiftFileList (in target 'BroadcastExtension' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/BroadcastExtension.SwiftFileList

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/BroadcastExtension.SwiftConstValuesFileList (in target 'BroadcastExtension' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/BroadcastExtension.SwiftConstValuesFileList

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/BroadcastExtension.LinkFileList (in target 'BroadcastExtension' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/BroadcastExtension.LinkFileList

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/BroadcastExtension-OutputFileMap.json (in target 'BroadcastExtension' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/BroadcastExtension-OutputFileMap.json

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension.hmap (in target 'BroadcastExtension' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension.hmap

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension.DependencyMetadataFileList (in target 'BroadcastExtension' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension.DependencyMetadataFileList

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-project-headers.hmap (in target 'BroadcastExtension' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-project-headers.hmap

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-own-target-headers.hmap (in target 'BroadcastExtension' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-own-target-headers.hmap

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-generated-files.hmap (in target 'BroadcastExtension' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-generated-files.hmap

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-all-target-headers.hmap (in target 'BroadcastExtension' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-all-target-headers.hmap

WriteAuxiliaryFile /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-all-non-framework-target-headers.hmap (in target 'BroadcastExtension' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    write-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-all-non-framework-target-headers.hmap

MkDir /Users/runner/work/232323/232323/ios/build/Build/Products/Release-iphoneos/UdpCast.app/PlugIns (in target 'UdpCast' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    /bin/mkdir -p /Users/runner/work/232323/232323/ios/build/Build/Products/Release-iphoneos/UdpCast.app/PlugIns

MkDir /Users/runner/work/232323/232323/ios/build/Build/Products/Release-iphoneos/UdpCast.app (in target 'UdpCast' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    /bin/mkdir -p /Users/runner/work/232323/232323/ios/build/Build/Products/Release-iphoneos/UdpCast.app

MkDir /Users/runner/work/232323/232323/ios/build/Build/Products/Release-iphoneos/BroadcastExtension.appex (in target 'BroadcastExtension' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    /bin/mkdir -p /Users/runner/work/232323/232323/ios/build/Build/Products/Release-iphoneos/BroadcastExtension.appex

ProcessInfoPlistFile /Users/runner/work/232323/232323/ios/build/Build/Products/Release-iphoneos/BroadcastExtension.appex/Info.plist /Users/runner/work/232323/232323/ios/UdpCast/BroadcastExtension/Info.plist (in target 'BroadcastExtension' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    builtin-infoPlistUtility /Users/runner/work/232323/232323/ios/UdpCast/BroadcastExtension/Info.plist -producttype com.apple.product-type.app-extension -expandbuildsettings -format binary -platform iphoneos -requiredArchitecture arm64 -o /Users/runner/work/232323/232323/ios/build/Build/Products/Release-iphoneos/BroadcastExtension.appex/Info.plist

SwiftDriver BroadcastExtension normal arm64 com.apple.xcode.tools.swift.compiler (in target 'BroadcastExtension' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    builtin-SwiftDriver -- /Applications/Xcode_16.2.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc -module-name BroadcastExtension -O -whole-module-optimization -enforce-exclusivity\=checked @/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/BroadcastExtension.SwiftFileList -enable-bare-slash-regex -enable-experimental-feature DebugDescriptionMacro -sdk /Applications/Xcode_16.2.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS18.2.sdk -target arm64-apple-ios16.0 -g -module-cache-path /Users/runner/work/232323/232323/ios/build/ModuleCache.noindex -Xfrontend -serialize-debugging-options -application-extension -swift-version 5 -I /Users/runner/work/232323/232323/ios/build/Build/Products/Release-iphoneos -F /Users/runner/work/232323/232323/ios/build/Build/Products/Release-iphoneos -c -num-threads 3 -Xcc -ivfsstatcache -Xcc /Users/runner/work/232323/232323/ios/build/SDKStatCaches.noindex/iphoneos18.2-22C146-6f6929c68f51360d5ca70a73a7e0c2f9.sdkstatcache -output-file-map /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/BroadcastExtension-OutputFileMap.json -use-frontend-parseable-output -save-temps -no-color-diagnostics -serialize-diagnostics -emit-dependencies -emit-module -emit-module-path /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/BroadcastExtension.swiftmodule -validate-clang-modules-once -clang-build-session-file /Users/runner/work/232323/232323/ios/build/ModuleCache.noindex/Session.modulevalidation -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/swift-overrides.hmap -emit-const-values -Xfrontend -const-gather-protocols-file -Xfrontend /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/BroadcastExtension_const_extract_protocols.json -Xcc -iquote -Xcc /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-generated-files.hmap -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-own-target-headers.hmap -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-all-target-headers.hmap -Xcc -iquote -Xcc /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-project-headers.hmap -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Products/Release-iphoneos/include -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/DerivedSources-normal/arm64 -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/DerivedSources/arm64 -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/DerivedSources -emit-objc-header -emit-objc-header-path /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/BroadcastExtension-Swift.h -working-directory /Users/runner/work/232323/232323/ios -no-emit-module-separately-wmo

SwiftDriver\ Compilation BroadcastExtension normal arm64 com.apple.xcode.tools.swift.compiler (in target 'BroadcastExtension' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    builtin-Swift-Compilation -- /Applications/Xcode_16.2.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc -module-name BroadcastExtension -O -whole-module-optimization -enforce-exclusivity\=checked @/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/BroadcastExtension.SwiftFileList -enable-bare-slash-regex -enable-experimental-feature DebugDescriptionMacro -sdk /Applications/Xcode_16.2.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS18.2.sdk -target arm64-apple-ios16.0 -g -module-cache-path /Users/runner/work/232323/232323/ios/build/ModuleCache.noindex -Xfrontend -serialize-debugging-options -application-extension -swift-version 5 -I /Users/runner/work/232323/232323/ios/build/Build/Products/Release-iphoneos -F /Users/runner/work/232323/232323/ios/build/Build/Products/Release-iphoneos -c -num-threads 3 -Xcc -ivfsstatcache -Xcc /Users/runner/work/232323/232323/ios/build/SDKStatCaches.noindex/iphoneos18.2-22C146-6f6929c68f51360d5ca70a73a7e0c2f9.sdkstatcache -output-file-map /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/BroadcastExtension-OutputFileMap.json -use-frontend-parseable-output -save-temps -no-color-diagnostics -serialize-diagnostics -emit-dependencies -emit-module -emit-module-path /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/BroadcastExtension.swiftmodule -validate-clang-modules-once -clang-build-session-file /Users/runner/work/232323/232323/ios/build/ModuleCache.noindex/Session.modulevalidation -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/swift-overrides.hmap -emit-const-values -Xfrontend -const-gather-protocols-file -Xfrontend /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/BroadcastExtension_const_extract_protocols.json -Xcc -iquote -Xcc /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-generated-files.hmap -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-own-target-headers.hmap -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-all-target-headers.hmap -Xcc -iquote -Xcc /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-project-headers.hmap -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Products/Release-iphoneos/include -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/DerivedSources-normal/arm64 -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/DerivedSources/arm64 -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/DerivedSources -emit-objc-header -emit-objc-header-path /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/BroadcastExtension-Swift.h -working-directory /Users/runner/work/232323/232323/ios -no-emit-module-separately-wmo

SwiftCompile normal arm64 Compiling\ CastConfig.swift,\ CastProtocol.swift,\ H264Encoder.swift,\ SampleHandler.swift,\ UdpDiscovery.swift,\ UdpSender.swift /Users/runner/work/232323/232323/ios/UdpCast/Shared/CastConfig.swift /Users/runner/work/232323/232323/ios/UdpCast/Shared/CastProtocol.swift /Users/runner/work/232323/232323/ios/UdpCast/Shared/H264Encoder.swift /Users/runner/work/232323/232323/ios/UdpCast/BroadcastExtension/SampleHandler.swift /Users/runner/work/232323/232323/ios/UdpCast/Shared/UdpDiscovery.swift /Users/runner/work/232323/232323/ios/UdpCast/Shared/UdpSender.swift (in target 'BroadcastExtension' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    builtin-swiftTaskExecution -- /Applications/Xcode_16.2.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swift-frontend -frontend -c /Users/runner/work/232323/232323/ios/UdpCast/Shared/CastConfig.swift /Users/runner/work/232323/232323/ios/UdpCast/Shared/CastProtocol.swift /Users/runner/work/232323/232323/ios/UdpCast/Shared/H264Encoder.swift /Users/runner/work/232323/232323/ios/UdpCast/BroadcastExtension/SampleHandler.swift /Users/runner/work/232323/232323/ios/UdpCast/Shared/UdpDiscovery.swift /Users/runner/work/232323/232323/ios/UdpCast/Shared/UdpSender.swift -supplementary-output-file-map /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/supplementaryOutputs-1 -target arm64-apple-ios16.0 -Xllvm -aarch64-use-tbi -enable-objc-interop -stack-check -sdk /Applications/Xcode_16.2.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS18.2.sdk -I /Users/runner/work/232323/232323/ios/build/Build/Products/Release-iphoneos -F /Users/runner/work/232323/232323/ios/build/Build/Products/Release-iphoneos -no-color-diagnostics -application-extension -g -debug-info-format\=dwarf -dwarf-version\=4 -module-cache-path /Users/runner/work/232323/232323/ios/build/ModuleCache.noindex -swift-version 5 -enforce-exclusivity\=checked -O -serialize-debugging-options -const-gather-protocols-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/BroadcastExtension_const_extract_protocols.json -enable-experimental-feature DebugDescriptionMacro -enable-bare-slash-regex -empty-abi-descriptor -validate-clang-modules-once -clang-build-session-file /Users/runner/work/232323/232323/ios/build/ModuleCache.noindex/Session.modulevalidation -Xcc -working-directory -Xcc /Users/runner/work/232323/232323/ios -resource-dir /Applications/Xcode_16.2.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/swift -file-compilation-dir /Users/runner/work/232323/232323/ios -Xcc -ivfsstatcache -Xcc /Users/runner/work/232323/232323/ios/build/SDKStatCaches.noindex/iphoneos18.2-22C146-6f6929c68f51360d5ca70a73a7e0c2f9.sdkstatcache -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/swift-overrides.hmap -Xcc -iquote -Xcc /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-generated-files.hmap -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-own-target-headers.hmap -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-all-target-headers.hmap -Xcc -iquote -Xcc /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-project-headers.hmap -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Products/Release-iphoneos/include -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/DerivedSources-normal/arm64 -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/DerivedSources/arm64 -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/DerivedSources -module-name BroadcastExtension -frontend-parseable-output -disable-clang-spi -target-sdk-version 18.2 -target-sdk-name iphoneos18.2 -external-plugin-path /Applications/Xcode_16.2.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/usr/lib/swift/host/plugins\#/Applications/Xcode_16.2.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/usr/bin/swift-plugin-server -external-plugin-path /Applications/Xcode_16.2.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/usr/local/lib/swift/host/plugins\#/Applications/Xcode_16.2.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/usr/bin/swift-plugin-server -plugin-path /Applications/Xcode_16.2.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/swift/host/plugins -plugin-path /Applications/Xcode_16.2.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/local/lib/swift/host/plugins -enable-default-cmo -num-threads 3 -o /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/CastConfig.o -o /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/CastProtocol.o -o /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/H264Encoder.o -o /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/SampleHandler.o -o /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/UdpDiscovery.o -o /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/UdpSender.o -index-unit-output-path /UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/CastConfig.o -index-unit-output-path /UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/CastProtocol.o -index-unit-output-path /UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/H264Encoder.o -index-unit-output-path /UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/SampleHandler.o -index-unit-output-path /UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/UdpDiscovery.o -index-unit-output-path /UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/UdpSender.o

CompileSwift normal arm64 (in target 'BroadcastExtension' from project 'UdpCast')
    cd /Users/runner/work/232323/232323/ios
    /Applications/Xcode_16.2.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swift-frontend -c /Users/runner/work/232323/232323/ios/UdpCast/Shared/CastConfig.swift /Users/runner/work/232323/232323/ios/UdpCast/Shared/CastProtocol.swift /Users/runner/work/232323/232323/ios/UdpCast/Shared/H264Encoder.swift /Users/runner/work/232323/232323/ios/UdpCast/BroadcastExtension/SampleHandler.swift /Users/runner/work/232323/232323/ios/UdpCast/Shared/UdpDiscovery.swift /Users/runner/work/232323/232323/ios/UdpCast/Shared/UdpSender.swift -supplementary-output-file-map /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/supplementaryOutputs-1 -target arm64-apple-ios16.0 -Xllvm -aarch64-use-tbi -enable-objc-interop -stack-check -sdk /Applications/Xcode_16.2.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS18.2.sdk -I /Users/runner/work/232323/232323/ios/build/Build/Products/Release-iphoneos -F /Users/runner/work/232323/232323/ios/build/Build/Products/Release-iphoneos -no-color-diagnostics -application-extension -g -debug-info-format\=dwarf -dwarf-version\=4 -module-cache-path /Users/runner/work/232323/232323/ios/build/ModuleCache.noindex -swift-version 5 -enforce-exclusivity\=checked -O -serialize-debugging-options -const-gather-protocols-file /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/BroadcastExtension_const_extract_protocols.json -enable-experimental-feature DebugDescriptionMacro -enable-bare-slash-regex -empty-abi-descriptor -validate-clang-modules-once -clang-build-session-file /Users/runner/work/232323/232323/ios/build/ModuleCache.noindex/Session.modulevalidation -Xcc -working-directory -Xcc /Users/runner/work/232323/232323/ios -resource-dir /Applications/Xcode_16.2.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/swift -file-compilation-dir /Users/runner/work/232323/232323/ios -Xcc -ivfsstatcache -Xcc /Users/runner/work/232323/232323/ios/build/SDKStatCaches.noindex/iphoneos18.2-22C146-6f6929c68f51360d5ca70a73a7e0c2f9.sdkstatcache -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/swift-overrides.hmap -Xcc -iquote -Xcc /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-generated-files.hmap -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-own-target-headers.hmap -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-all-target-headers.hmap -Xcc -iquote -Xcc /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/BroadcastExtension-project-headers.hmap -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Products/Release-iphoneos/include -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/DerivedSources-normal/arm64 -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/DerivedSources/arm64 -Xcc -I/Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/DerivedSources -module-name BroadcastExtension -frontend-parseable-output -disable-clang-spi -target-sdk-version 18.2 -target-sdk-name iphoneos18.2 -external-plugin-path /Applications/Xcode_16.2.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/usr/lib/swift/host/plugins\#/Applications/Xcode_16.2.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/usr/bin/swift-plugin-server -external-plugin-path /Applications/Xcode_16.2.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/usr/local/lib/swift/host/plugins\#/Applications/Xcode_16.2.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/usr/bin/swift-plugin-server -plugin-path /Applications/Xcode_16.2.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/swift/host/plugins -plugin-path /Applications/Xcode_16.2.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/local/lib/swift/host/plugins -enable-default-cmo -num-threads 3 -o /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/CastConfig.o -o /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/CastProtocol.o -o /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/H264Encoder.o -o /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/SampleHandler.o -o /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/UdpDiscovery.o -o /Users/runner/work/232323/232323/ios/build/Build/Intermediates.noindex/UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/UdpSender.o -index-unit-output-path /UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/CastConfig.o -index-unit-output-path /UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/CastProtocol.o -index-unit-output-path /UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/H264Encoder.o -index-unit-output-path /UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/SampleHandler.o -index-unit-output-path /UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/UdpDiscovery.o -index-unit-output-path /UdpCast.build/Release-iphoneos/BroadcastExtension.build/Objects-normal/arm64/UdpSender.o
/Users/runner/work/232323/232323/ios/UdpCast/Shared/UdpDiscovery.swift:309:37: error: cannot convert value of type 'UnsafePointer<sockaddr>' to expected argument type 'UnsafeMutablePointer<sockaddr>'
                        numericHost(sa)
                                    ^

note: Disabling previews because SWIFT_VERSION is set and SWIFT_OPTIMIZATION_LEVEL=-O, expected -Onone (in target 'UdpCast' from project 'UdpCast')
note: Disabling previews because SWIFT_VERSION is set and SWIFT_OPTIMIZATION_LEVEL=-O, expected -Onone (in target 'BroadcastExtension' from project 'UdpCast')
** BUILD FAILED **


The following build commands failed:
	CompileSwift normal arm64 (in target 'BroadcastExtension' from project 'UdpCast')
	SwiftCompile normal arm64 Compiling\ CastConfig.swift,\ CastProtocol.swift,\ H264Encoder.swift,\ SampleHandler.swift,\ UdpDiscovery.swift,\ UdpSender.swift /Users/runner/work/232323/232323/ios/UdpCast/Shared/CastConfig.swift /Users/runner/work/232323/232323/ios/UdpCast/Shared/CastProtocol.swift /Users/runner/work/232323/232323/ios/UdpCast/Shared/H264Encoder.swift /Users/runner/work/232323/232323/ios/UdpCast/BroadcastExtension/SampleHandler.swift /Users/runner/work/232323/232323/ios/UdpCast/Shared/UdpDiscovery.swift /Users/runner/work/232323/232323/ios/UdpCast/Shared/UdpSender.swift (in target 'BroadcastExtension' from project 'UdpCast')
	Building project UdpCast with scheme UdpCast and configuration Release
(3 failures)
```

## Verify
```
(未执行)
```

## Package
```
(未执行)
```
