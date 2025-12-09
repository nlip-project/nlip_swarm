import { useCallback } from 'react';
import { Alert } from 'react-native';
import * as ImagePicker from 'expo-image-picker';

type PickerOptionsWithMessage = Partial<ImagePicker.ImagePickerOptions> & {
    permissionMessage?: string;
};

interface UseImageAttachmentOptions {
    onImageSelected: (uri: string) => void;
    onError?: (message: string) => void;
    cameraOptions?: PickerOptionsWithMessage;
    libraryOptions?: PickerOptionsWithMessage;
}

const DEFAULT_CAMERA_PERMISSION = 'Camera permission is required to take a photo.';
const DEFAULT_LIBRARY_PERMISSION = 'Photo library permission is required to choose a photo.';

export function useImageAttachment({
    onImageSelected,
    onError,
    cameraOptions,
    libraryOptions,
}: UseImageAttachmentOptions) {
    const handleSelection = useCallback(
        (result: ImagePicker.ImagePickerResult) => {
            if (!result.canceled && result.assets && result.assets.length > 0) {
                const asset = result.assets[0];
                if (asset.uri) {
                    onImageSelected(asset.uri);
                    return true;
                }
            }
            return false;
        },
        [onImageSelected]
    );

    const openCamera = useCallback(async () => {
        const { permissionMessage, ...cameraConfig } = cameraOptions ?? {};
        const { status } = await ImagePicker.requestCameraPermissionsAsync();
        if (status !== 'granted') {
            const message = permissionMessage || DEFAULT_CAMERA_PERMISSION;
            Alert.alert('Permission required', message);
            onError?.(message);
            return false;
        }

        try {
            const result = await ImagePicker.launchCameraAsync({
                allowsEditing: false,
                quality: 0.8,
                ...(cameraConfig as ImagePicker.ImagePickerOptions),
            });
            return handleSelection(result);
        } catch (error) {
            console.warn('Failed to open camera', error);
            const message = 'Failed to open camera';
            Alert.alert('Error', message);
            onError?.(message);
            return false;
        }
    }, [cameraOptions, handleSelection, onError]);

    const pickImageFromLibrary = useCallback(async () => {
        const { permissionMessage, ...libraryConfig } = libraryOptions ?? {};
        const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
        if (status !== 'granted') {
            const message = permissionMessage || DEFAULT_LIBRARY_PERMISSION;
            Alert.alert('Permission required', message);
            onError?.(message);
            return false;
        }

        try {
            const result = await ImagePicker.launchImageLibraryAsync({
                mediaTypes: ['images'],
                allowsEditing: false,
                quality: 0.8,
                allowsMultipleSelection: false,
                ...(libraryConfig as ImagePicker.ImagePickerOptions),
            });
            return handleSelection(result);
        } catch (error) {
            console.warn('Failed to open photo library', error);
            const message = 'Failed to open photo library';
            Alert.alert('Error', message);
            onError?.(message);
            return false;
        }
    }, [handleSelection, libraryOptions, onError]);

    return { openCamera, pickImageFromLibrary };
}
