import { StyleSheet, TextInput, View } from 'react-native';


export default function TabThreeScreen() {
    return (
        <View style={styles.container}>
            <TextInput style={styles.textInput} />
            
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
    },
    textInput: {
        // On the bottom of the div
        position: 'absolute',
        bottom: 0,
        // Full width
        width: '90%',
        // Height
        height: 40,
        // Border
        borderColor: 'gray',
        borderWidth: 1,
        
    },
});
